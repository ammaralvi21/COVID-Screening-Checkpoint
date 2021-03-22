/* USER CODE BEGIN Header */
/**
  ******************************************************************************
  * @file           : main.c
  * @brief          : Main program body
  ******************************************************************************
  * @attention
  *
  * <h2><center>&copy; Copyright (c) 2021 STMicroelectronics.
  * All rights reserved.</center></h2>
  *
  * This software component is licensed by ST under BSD 3-Clause license,
  * the "License"; You may not use this file except in compliance with the
  * License. You may obtain a copy of the License at:
* *                        opensource.org/licenses/BSD-3-Clause
*	
* FILENAME :        main.c             
*
* DESCRIPTION :
*       main implementation for sensor interface. 
				It features a registered I2C slave interrupt callback functions that
				determines which external device the Stm32 is polling.
				It contains interface to the following devices:
					- Infrared Temerature Reading using I2C
					- Infrared SPO2 readings.
						-> This is done by reading raw Infrared data and performing 
							 algorithmic calculations in MAX30102.c and algorithm.c.
						-> The code for this was ported from: 
						   https://github.com/MaximIntegratedRefDesTeam/RD117_ARDUINO
							 Which is an Arduino code that we transformed to work with 
							 the stm32 microcontroller.
					- Reading two Analog infrared sensor, performing ADC conversion and
					  encoding information for which sensor is being used
					- Motor driver output with digital IR sensor input. It reads the digit 
					  input and drives the motor driver to dispense hand sanitizer
*
* PUBLIC FUNCTIONS :
*       int     FM_CompressFile( FileHandle )
*       int     FM_DecompressFile( FileHandle )
*
* NOTES :
*       These functions are a part of the FM suite;
*       See IMS FM0121 for detailed description.
*
*       Copyright A.N.Other Co. 1990, 1995.  All rights reserved.
*
* AUTHOR :    Arthur Other        START DATE :    16 Jan 99
*
* CHANGES :
*
* REF NO  VERSION DATE    WHO     DETAIL
* F21/33  A.03.04 22Jan99 JR      Function CalcHuffman corrected
*
*
**********************************************************************************/
/* USER CODE END Header */
/* Includes ------------------------------------------------------------------*/
#include "main.h"

/* Private includes ----------------------------------------------------------*/
/* USER CODE BEGIN Includes */

/* USER CODE END Includes */

/* Private typedef -----------------------------------------------------------*/
/* USER CODE BEGIN PTD */
//State Enumeration used in switch statement
typedef enum 
{ 
	IR_UI,
	TEMP,
	SPO2,
	SANITIZE,
	IDLE
	
} SenseState;

/* USER CODE END PTD */

/* Private define ------------------------------------------------------------*/
/* USER CODE BEGIN PD */
#define MAX_BRIGHTNESS 255
/* USER CODE END PD */

/* Private macro -------------------------------------------------------------*/
/* USER CODE BEGIN PM */
//Codes used by Jetson Nano to read different sensors
#define I2C_SET_TEMP 0x01
#define I2C_SET_SPO2 0x02
#define I2C_SET_UI 0x03
#define I2C_SET_SANITIZER 0x04
#define I2C_SET_IDLE 0x05


#define MLX_I2CADR  0x5A       	// MLX90614 I2C address
#define MLX90614_TAMB	   0x06		//Ambient Temp Register
#define MLX90614_TOBJ1   0x07		//Object 1 Temp Register
#define MLX90614_TOBJ2   0x08		//Object 2 Temp Register

/* USER CODE END PM */

/* Private variables ---------------------------------------------------------*/
ADC_HandleTypeDef hadc1;

I2C_HandleTypeDef hi2c1;
I2C_HandleTypeDef hi2c2;

/* USER CODE BEGIN PV */
//-----------------------------------------------------------------------------------------------
//Variables for spo2 sensor ported from https://github.com/MaximIntegratedRefDesTeam/RD117_ARDUINO
uint16_t aun_ir_buffer[100]; //infrared LED sensor data
uint16_t aun_red_buffer[100];  //red LED sensor data
int32_t n_ir_buffer_length; //data length
int32_t n_spo2;  //SPO2 value
int8_t ch_spo2_valid;  //indicator to show if the SPO2 calculation is valid
int32_t n_heart_rate; //heart rate value
int8_t  ch_hr_valid;  //indicator to show if the heart rate calculation is valid
uint8_t uch_dummy;
//-----------------------------------------------------------------------------------------------
//Initial state change 
char myval[5];
bool state_change = true;
/* USER CODE END PV */

/* Private function prototypes -----------------------------------------------*/
void SystemClock_Config(void);
static void MX_GPIO_Init(void);
static void MX_ADC1_Init(void);
static void MX_I2C2_Init(void);
static void MX_I2C1_Init(void);
static void MX_NVIC_Init(void);
/* USER CODE BEGIN PFP */
//Enable different ADC Channel
void ADC_CH6_Enable(void);
void ADC_CH5_Enable(void);

/* USER CODE END PFP */

/* Private user code ---------------------------------------------------------*/
/* USER CODE BEGIN 0 */
//Declating state variable
SenseState g_State = IR_UI;

//Right and Left IR UI Analog value
volatile uint16_t IR_Right = 0;
volatile uint16_t IR_Left = 0;

//I2C to Jetson Nano Transmit and Reciever 8 bit buffer
volatile uint8_t g_i2c_rx_buff = 0;
volatile uint8_t g_i2c_tx_buff = 0;

//Encoded value to send to jetson nano for IR UI
volatile uint8_t g_IR_UI_status = 0;

//Temperature buffer and storage variables
volatile uint8_t temperature_buffer[2];
volatile int temp_local_read1;
volatile uint32_t upper_byte = 0;
volatile uint32_t lower_byte = 0;
volatile uint32_t int_temp;
/* USER CODE END 0 */

/**
  * @brief  The application entry point.
  * @retval int
  */
int main(void)
{
  /* USER CODE BEGIN 1 */
	
  /* USER CODE END 1 */

  /* MCU Configuration--------------------------------------------------------*/

  /* Reset of all peripherals, Initializes the Flash interface and the Systick. */
  HAL_Init();

  /* USER CODE BEGIN Init */

  /* USER CODE END Init */

  /* Configure the system clock */
  SystemClock_Config();

  /* USER CODE BEGIN SysInit */

  /* USER CODE END SysInit */

  /* Initialize all configured peripherals */
  MX_GPIO_Init();
  MX_ADC1_Init();
  MX_I2C2_Init();
  MX_I2C1_Init();

  /* Initialize interrupts */
  MX_NVIC_Init();
  /* USER CODE BEGIN 2 */
	
	//Initialize I2C slave interrupt listen from Jetson Nano
	g_i2c_rx_buff = 0;
	HAL_I2C_EnableListen_IT(&hi2c2);
	

  /* USER CODE END 2 */

  /* Infinite loop */
  /* USER CODE BEGIN WHILE */
	//-----------------------------------------------------------------------------------------------
	//Variables for spo2 sensor ported from https://github.com/MaximIntegratedRefDesTeam/RD117_ARDUINO
	uint32_t un_min, un_max, un_prev_data, un_brightness;  //variables to calculate the on-board LED brightness that reflects the heartbeats
	int32_t i;
	float f_temp;
	un_brightness=0;
	un_min=0x3FFFF;
	un_max=0;
	//---End of ported code---------------------------------------------------------------------
	// Set initial state to IDLE
	g_State = IDLE;

  while (1)
  {		
		switch (g_State)
		{	
			case IR_UI:
				// Staring ADC conversion on Channel 6 (Right Infrared Sensor)
				ADC_CH6_Enable();
				HAL_ADC_Start(&hadc1);
				HAL_ADC_PollForConversion(&hadc1, 1000);
				IR_Right = HAL_ADC_GetValue(&hadc1);
				HAL_ADC_Stop(&hadc1);
				// Staring ADC conversion on Channel 5 (Left Infrared Sensor)
				ADC_CH5_Enable();
				HAL_ADC_Start(&hadc1);
				HAL_ADC_PollForConversion(&hadc1, 1000);
				IR_Left = HAL_ADC_GetValue(&hadc1);
				HAL_ADC_Stop(&hadc1);
				// Comparing Analog values of the IR Sensors with threshold for
				//  ...hand detection
				if ((IR_Right > 800) && (IR_Left < 800))
				{
					g_IR_UI_status = 0x1;
				}
				else if((IR_Right < 800) && (IR_Left > 800))
				{
					g_IR_UI_status = 0x4;
				}
				else if ((IR_Right > 800) && (IR_Left > 800))
				{
					g_IR_UI_status = 0x9;
				}
				else
				{
					g_IR_UI_status = 0xF;
				}
				//Output IR status to transmit buffer
				g_i2c_tx_buff = g_IR_UI_status;

				HAL_Delay(50);
				break;
			case TEMP:
				
				//I2C1 IR Register read from MLX90614
				HAL_I2C_Mem_Read(&hi2c1,MLX_I2CADR<<1, MLX90614_TOBJ1, 1, (uint8_t *)temperature_buffer, sizeof(temperature_buffer), 100);
				upper_byte = temperature_buffer[1];
				lower_byte = temperature_buffer[0];
				int_temp = (upper_byte << 8)| lower_byte;
				//temperature = int_temp*0.02 - 273.15; //Formula from data sheet for temp calculation but omits decimals
				temp_local_read1 = (int_temp << 1) - 27315; //Temp of Object in front of Sensor
				g_i2c_tx_buff = temp_local_read1/20;
				HAL_Delay(50);

				break;
			case SPO2:
				if (state_change) //Initial State change
				{	
//--------------------------------------------------------------------------------------------------------------------------
//-------------Main code for spo2 sensor ported from https://github.com/MaximIntegratedRefDesTeam/RD117_ARDUINO-------------
					
					n_ir_buffer_length=100;  //buffer length of 100 stores 4 seconds of samples running at 25sps
					//read the first 100 samples, and determine the signal range
					for(i=0;i<n_ir_buffer_length;i++)
					{
						while(HAL_GPIO_ReadPin (GPIOB, GPIO_PIN_8));  //wait until the interrupt pin asserts
						maxim_max30102_read_fifo((aun_red_buffer+i), (aun_ir_buffer+i));  //read from MAX30102 FIFO
						
						if(un_min>aun_red_buffer[i])
							un_min=aun_red_buffer[i];  //update signal min
						if(un_max<aun_red_buffer[i])
							un_max=aun_red_buffer[i];  //update signal max

					}
					un_prev_data=aun_red_buffer[i];
					//calculate heart rate and SpO2 after first 100 samples (first 4 seconds of samples)
					maxim_heart_rate_and_oxygen_saturation(aun_ir_buffer, n_ir_buffer_length, aun_red_buffer, &n_spo2, &ch_spo2_valid, &n_heart_rate, &ch_hr_valid); 
					

					maxim_max30102_init(&hi2c1);
					state_change = false;
				}
				
				i=0;
				un_min=0x3FFFF;
				un_max=0;

				//dumping the first 25 sets of samples in the memory and shift the last 75 sets of samples to the top
				for(i=25;i<100;i++)
				{
					aun_red_buffer[i-25]=aun_red_buffer[i];
					aun_ir_buffer[i-25]=aun_ir_buffer[i];

				//update the signal min and max
					if(un_min>aun_red_buffer[i])
						un_min=aun_red_buffer[i];
					if(un_max<aun_red_buffer[i])
						un_max=aun_red_buffer[i];
				}

				//take 25 sets of samples before calculating the heart rate.
				for(i=75;i<100;i++)
				{
					un_prev_data=aun_red_buffer[i-1];
					while(HAL_GPIO_ReadPin (GPIOB, GPIO_PIN_8));//Interrupt
					//digitalWrite(9, !digitalRead(9));
					maxim_max30102_read_fifo((aun_red_buffer+i), (aun_ir_buffer+i));

					//calculate the brightness of the LED
					if(aun_red_buffer[i]>un_prev_data)
					{
						f_temp=aun_red_buffer[i]-un_prev_data;
						f_temp/=(un_max-un_min);
						f_temp*=MAX_BRIGHTNESS;
						f_temp=un_brightness-f_temp;
					if(f_temp<0)
						un_brightness=0;
					else
						un_brightness=(int)f_temp;
					}
					else
					{
						f_temp=un_prev_data-aun_red_buffer[i];
						f_temp/=(un_max-un_min);
						f_temp*=MAX_BRIGHTNESS;
						un_brightness+=(int)f_temp;
						if(un_brightness>MAX_BRIGHTNESS)
							un_brightness=MAX_BRIGHTNESS;
					}

					maxim_heart_rate_and_oxygen_saturation(aun_ir_buffer, n_ir_buffer_length, aun_red_buffer, &n_spo2, &ch_spo2_valid, &n_heart_rate, &ch_hr_valid); 

//-------------End of ported from https://github.com/MaximIntegratedRefDesTeam/RD117_ARDUINO-------------
//--------------------------------------------------------------------------------------------------------------------------					

					//Send the spo2 value to I2C global transmit buffer					
					if (ch_spo2_valid)
					{
						g_i2c_tx_buff = n_spo2;
					}
					else 
					{
						g_i2c_tx_buff = 0xFF;
					}
				}
				break;
			case SANITIZE:
				/* Sanitization Code */
				// Check if PC6 reads 0 value from Sanitizer IR sensor
				if(HAL_GPIO_ReadPin(GPIOC, GPIO_PIN_6) == 0)
				{
					HAL_GPIO_TogglePin(GPIOC, GPIO_PIN_7); //pump on
					g_i2c_tx_buff = 1;
					HAL_Delay(1000); //delay for 1 seconds/pump dispense time				
					HAL_GPIO_TogglePin(GPIOC, GPIO_PIN_7); // pump off
					HAL_Delay(3000);
					g_i2c_tx_buff = 0;
				}
				
				HAL_Delay(50);
				break;
			case IDLE:
				HAL_Delay(50);
				break;
			}
    /* USER CODE END WHILE */

    /* USER CODE BEGIN 3 */
  }
  /* USER CODE END 3 */
}

/**
  * @brief System Clock Configuration
  * @retval None
  */
void SystemClock_Config(void)
{
  RCC_OscInitTypeDef RCC_OscInitStruct = {0};
  RCC_ClkInitTypeDef RCC_ClkInitStruct = {0};
  RCC_PeriphCLKInitTypeDef PeriphClkInit = {0};

  /** Initializes the RCC Oscillators according to the specified parameters
  * in the RCC_OscInitTypeDef structure.
  */
  RCC_OscInitStruct.OscillatorType = RCC_OSCILLATORTYPE_HSE;
  RCC_OscInitStruct.HSEState = RCC_HSE_ON;
  RCC_OscInitStruct.HSEPredivValue = RCC_HSE_PREDIV_DIV1;
  RCC_OscInitStruct.PLL.PLLState = RCC_PLL_ON;
  RCC_OscInitStruct.PLL.PLLSource = RCC_PLLSOURCE_HSE;
  RCC_OscInitStruct.PLL.PLLMUL = RCC_PLL_MUL2;
  if (HAL_RCC_OscConfig(&RCC_OscInitStruct) != HAL_OK)
  {
    Error_Handler();
  }
  /** Initializes the CPU, AHB and APB buses clocks
  */
  RCC_ClkInitStruct.ClockType = RCC_CLOCKTYPE_HCLK|RCC_CLOCKTYPE_SYSCLK
                              |RCC_CLOCKTYPE_PCLK1|RCC_CLOCKTYPE_PCLK2;
  RCC_ClkInitStruct.SYSCLKSource = RCC_SYSCLKSOURCE_PLLCLK;
  RCC_ClkInitStruct.AHBCLKDivider = RCC_SYSCLK_DIV1;
  RCC_ClkInitStruct.APB1CLKDivider = RCC_HCLK_DIV1;
  RCC_ClkInitStruct.APB2CLKDivider = RCC_HCLK_DIV1;

  if (HAL_RCC_ClockConfig(&RCC_ClkInitStruct, FLASH_LATENCY_0) != HAL_OK)
  {
    Error_Handler();
  }
  PeriphClkInit.PeriphClockSelection = RCC_PERIPHCLK_ADC;
  PeriphClkInit.AdcClockSelection = RCC_ADCPCLK2_DIV4;
  if (HAL_RCCEx_PeriphCLKConfig(&PeriphClkInit) != HAL_OK)
  {
    Error_Handler();
  }
}

/**
  * @brief NVIC Configuration.
  * @retval None
  */
static void MX_NVIC_Init(void)
{
  /* I2C2_EV_IRQn interrupt configuration */
  HAL_NVIC_SetPriority(I2C2_EV_IRQn, 0, 0);
  HAL_NVIC_EnableIRQ(I2C2_EV_IRQn);
  /* I2C2_ER_IRQn interrupt configuration */
  HAL_NVIC_SetPriority(I2C2_ER_IRQn, 0, 0);
  HAL_NVIC_EnableIRQ(I2C2_ER_IRQn);
}

/**
  * @brief ADC1 Initialization Function
  * @param None
  * @retval None
  */
static void MX_ADC1_Init(void)
{

  /* USER CODE BEGIN ADC1_Init 0 */

  /* USER CODE END ADC1_Init 0 */

  //ADC_ChannelConfTypeDef sConfig = {0};

  /* USER CODE BEGIN ADC1_Init 1 */

  /* USER CODE END ADC1_Init 1 */
  /** Common config
  */
  hadc1.Instance = ADC1;
  hadc1.Init.ScanConvMode = ADC_SCAN_ENABLE;
  hadc1.Init.ContinuousConvMode = DISABLE;
  hadc1.Init.DiscontinuousConvMode = DISABLE;
  hadc1.Init.ExternalTrigConv = ADC_SOFTWARE_START;
  hadc1.Init.DataAlign = ADC_DATAALIGN_RIGHT;
  hadc1.Init.NbrOfConversion = 2;
  if (HAL_ADC_Init(&hadc1) != HAL_OK)
  {
    Error_Handler();
  }
  /** Configure Regular Channel
  */
//  sConfig.Channel = ADC_CHANNEL_5;
//  sConfig.Rank = ADC_REGULAR_RANK_1;
//  sConfig.SamplingTime = ADC_SAMPLETIME_71CYCLES_5;
//  if (HAL_ADC_ConfigChannel(&hadc1, &sConfig) != HAL_OK)
//  {
//    Error_Handler();
//  }
//  /** Configure Regular Channel
//  */
//  sConfig.Channel = ADC_CHANNEL_6;
//  sConfig.Rank = ADC_REGULAR_RANK_2;
//  if (HAL_ADC_ConfigChannel(&hadc1, &sConfig) != HAL_OK)
//  {
//    Error_Handler();
//  }
  /* USER CODE BEGIN ADC1_Init 2 */

  /* USER CODE END ADC1_Init 2 */

}

/**
  * @brief I2C1 Initialization Function
  * @param None
  * @retval None
  */
static void MX_I2C1_Init(void)
{

  /* USER CODE BEGIN I2C1_Init 0 */

  /* USER CODE END I2C1_Init 0 */

  /* USER CODE BEGIN I2C1_Init 1 */

  /* USER CODE END I2C1_Init 1 */
  hi2c1.Instance = I2C1;
  hi2c1.Init.ClockSpeed = 100000;
  hi2c1.Init.DutyCycle = I2C_DUTYCYCLE_2;
  hi2c1.Init.OwnAddress1 = 0;
  hi2c1.Init.AddressingMode = I2C_ADDRESSINGMODE_7BIT;
  hi2c1.Init.DualAddressMode = I2C_DUALADDRESS_DISABLE;
  hi2c1.Init.OwnAddress2 = 0;
  hi2c1.Init.GeneralCallMode = I2C_GENERALCALL_DISABLE;
  hi2c1.Init.NoStretchMode = I2C_NOSTRETCH_DISABLE;
  if (HAL_I2C_Init(&hi2c1) != HAL_OK)
  {
    Error_Handler();
  }
  /* USER CODE BEGIN I2C1_Init 2 */

  /* USER CODE END I2C1_Init 2 */

}

/**
  * @brief I2C2 Initialization Function
  * @param None
  * @retval None
  */
static void MX_I2C2_Init(void)
{

  /* USER CODE BEGIN I2C2_Init 0 */

  /* USER CODE END I2C2_Init 0 */

  /* USER CODE BEGIN I2C2_Init 1 */

  /* USER CODE END I2C2_Init 1 */
  hi2c2.Instance = I2C2;
  hi2c2.Init.ClockSpeed = 100000;
  hi2c2.Init.DutyCycle = I2C_DUTYCYCLE_2;
  hi2c2.Init.OwnAddress1 = 128;
  hi2c2.Init.AddressingMode = I2C_ADDRESSINGMODE_7BIT;
  hi2c2.Init.DualAddressMode = I2C_DUALADDRESS_DISABLE;
  hi2c2.Init.OwnAddress2 = 0;
  hi2c2.Init.GeneralCallMode = I2C_GENERALCALL_DISABLE;
  hi2c2.Init.NoStretchMode = I2C_NOSTRETCH_DISABLE;
  if (HAL_I2C_Init(&hi2c2) != HAL_OK)
  {
    Error_Handler();
  }
  /* USER CODE BEGIN I2C2_Init 2 */

  /* USER CODE END I2C2_Init 2 */

}

/**
  * @brief GPIO Initialization Function
  * @param None
  * @retval None
  */
static void MX_GPIO_Init(void)
{
  GPIO_InitTypeDef GPIO_InitStruct = {0};

  /* GPIO Ports Clock Enable */
  __HAL_RCC_GPIOC_CLK_ENABLE();
  __HAL_RCC_GPIOD_CLK_ENABLE();
  __HAL_RCC_GPIOA_CLK_ENABLE();
  __HAL_RCC_GPIOB_CLK_ENABLE();

  /*Configure GPIO pin Output Level */
  HAL_GPIO_WritePin(GPIOC, GPIO_PIN_7|LD4_Pin|LD3_Pin, GPIO_PIN_RESET);

  /*Configure GPIO pin : PC6 */
  GPIO_InitStruct.Pin = GPIO_PIN_6;
  GPIO_InitStruct.Mode = GPIO_MODE_INPUT;
  GPIO_InitStruct.Pull = GPIO_NOPULL;
  HAL_GPIO_Init(GPIOC, &GPIO_InitStruct);

  /*Configure GPIO pins : PC7 LD4_Pin LD3_Pin */
  GPIO_InitStruct.Pin = GPIO_PIN_7|LD4_Pin|LD3_Pin;
  GPIO_InitStruct.Mode = GPIO_MODE_OUTPUT_PP;
  GPIO_InitStruct.Pull = GPIO_NOPULL;
  GPIO_InitStruct.Speed = GPIO_SPEED_FREQ_LOW;
  HAL_GPIO_Init(GPIOC, &GPIO_InitStruct);

  /*Configure GPIO pin : PB8 */
  GPIO_InitStruct.Pin = GPIO_PIN_8;
  GPIO_InitStruct.Mode = GPIO_MODE_INPUT;
  GPIO_InitStruct.Pull = GPIO_NOPULL;
  HAL_GPIO_Init(GPIOB, &GPIO_InitStruct);

}

/* USER CODE BEGIN 4 */

//I2C address callback function for communication to Jetson Nano
// Description: 
// This call back is genrated when correct I2C address for stm32 Slave is read from Jetson Nano I2C Master
// Transfer direction is determined from variable uint8_t TransferDirection provided by HAL library
// If the Direction is transmit, initialize the device for interupt recieve from Jetson Nano and
// ...store it in global recieve buffer
// If the Direction is recieve, initialize the device for interrupt transmit to Jetson Nano from
// ...from global transmit buffer
void HAL_I2C_AddrCallback (I2C_HandleTypeDef * hi2c, uint8_t TransferDirection, uint16_t AddrMatchCode)
{
	UNUSED(AddrMatchCode);
	
	switch (TransferDirection)
	{
		case I2C_DIRECTION_TRANSMIT:
			if (HAL_I2C_Slave_Seq_Receive_IT(&hi2c2, (uint8_t *) &g_i2c_rx_buff, 1, I2C_NEXT_FRAME) != HAL_OK) 
			{
				 Error_Handler();
			}

			break;
		case I2C_DIRECTION_RECEIVE:
			if (HAL_I2C_Slave_Seq_Transmit_IT(&hi2c2, (uint8_t *) &g_i2c_tx_buff, 1, I2C_LAST_FRAME) != HAL_OK) 
			{
				 Error_Handler();
			}
			break;
	}

}

//This callback function is called at the end of I2C transmit interrupt
//Set transmit buffer to 0.
void HAL_I2C_SlaveTxCpltCallback(I2C_HandleTypeDef *hi2c)
{
	//Send completion callback function 
	g_i2c_tx_buff = 0;

}

//This callback function is triggered after the I2C recieve interrupt ends.
// It takes the global i2c recieve buffer which contains the data recieved from
// ...Jetson Nano and configures the state.
void HAL_I2C_SlaveRxCpltCallback(I2C_HandleTypeDef *hi2c)
{
	//Receive completion callback function
	switch (g_i2c_rx_buff)
	{
		case I2C_SET_SPO2: 
			g_State = SPO2;
			state_change = true;
			g_i2c_tx_buff = 0;
			break;
		case I2C_SET_TEMP :
			g_State = TEMP;
			g_i2c_tx_buff = 0;
			break;
		case I2C_SET_UI :
			g_State = IR_UI;
			g_i2c_tx_buff = 0;
			break;
		case I2C_SET_SANITIZER :
			g_State = SANITIZE;
			g_i2c_tx_buff = 0;
			break;
		case I2C_SET_IDLE :
			g_State = IDLE;
			break;

	}
	
	g_i2c_rx_buff = 0;
	
	
}
// This is the last callback function triggered after any I2C communication
//.. which renables the interrupt listen on the I2C bus.
void HAL_I2C_ListenCpltCallback(I2C_HandleTypeDef *hi2c)
{ 
  HAL_I2C_EnableListen_IT(hi2c); // Restart
}

void ADC_CH5_Enable(void)
{
  /** Configure Regular Channel
  */
	ADC_ChannelConfTypeDef sConfig = {0};
  sConfig.Channel = ADC_CHANNEL_5;
  sConfig.Rank = 1;
  sConfig.SamplingTime = ADC_SAMPLETIME_7CYCLES_5;
  if (HAL_ADC_ConfigChannel(&hadc1, &sConfig) != HAL_OK)
  {
    Error_Handler();
  }
}
void ADC_CH6_Enable(void)
{
  /** Configure Regular Channel
  */
	ADC_ChannelConfTypeDef sConfig = {0};
  sConfig.Channel = ADC_CHANNEL_6;
  sConfig.Rank = 1;
	sConfig.SamplingTime = ADC_SAMPLETIME_7CYCLES_5;
  if (HAL_ADC_ConfigChannel(&hadc1, &sConfig) != HAL_OK)
  {
    Error_Handler();
  }
}
/* USER CODE END 4 */

/**
  * @brief  This function is executed in case of error occurrence.
  * @retval None
  */
void Error_Handler(void)
{
  /* USER CODE BEGIN Error_Handler_Debug */
  /* User can add his own implementation to report the HAL error return state */
  __disable_irq();
  while (1)
  {
  }
  /* USER CODE END Error_Handler_Debug */
}

#ifdef  USE_FULL_ASSERT
/**
  * @brief  Reports the name of the source file and the source line number
  *         where the assert_param error has occurred.
  * @param  file: pointer to the source file name
  * @param  line: assert_param error line source number
  * @retval None
  */
void assert_failed(uint8_t *file, uint32_t line)
{
  /* USER CODE BEGIN 6 */
  /* User can add his own implementation to report the file name and line number,
     ex: printf("Wrong parameters value: file %s on line %d\r\n", file, line) */
  /* USER CODE END 6 */
}
#endif /* USE_FULL_ASSERT */

/************************ (C) COPYRIGHT STMicroelectronics *****END OF FILE****/
