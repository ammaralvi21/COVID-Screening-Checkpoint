Questions = ("""<i>1/5</i>

Do you have any of the following <b>symptoms</b> which are new or worsened 
if associated with allergies, chronic or pre-existing conditions?
<span size="20000"> - Fever (temperature ≥ 38.0 Celsius)
 - cough
 - shortness of breath
 - difficulty breathing
 - sore throat
 - runny nose</span>
""", """<i>2/5</i>

Have you returned to Canada from outside the country <b>(including USA)</b> 
in the <b>past 14 days</b>?
""","""<i>3/5</i>

<b>In the past 14 days, at work or elsewhere, while not wearing appropriate
personal protective equipment:</b>
Did you have close contact with a person who has a probable or 
confirmed case of COVID-19?
""","""<i>4/5</i>

<b>In the past 14 days, at work or elsewhere, while not wearing appropriate
personal protective equipment:</b>
Did you have close contact with a person who had an acute respiratory 
illness that started within <b>14 days</b> of their close contact to someone 
with a probable or confirmed case of COVID-19?
""","""<i>5/5</i>

<b>In the past 14 days, at work or elsewhere, while not wearing appropriate
personal protective equipment:</b>
Did you have close contact with a person who had an acute respiratory 
illness who returned from travel outside of Canada in the <b>14 days</b> 
before they became sick?
""")

SurveyPrompt = """
We will ask a series of daily screening Questions to protect from
exposure during the COVID-19 pandemic and provide a safe environment

<small><i>The screening questionnaire is only meant as an aid and cannot diagnose you.
Consult a health care provider if you have medical questions.</i></small>
"""
SpO2Prompt = """
<b>We will now take your SpO2 reading.</b> 
Place your right finger underneath the device where the arrow points to.
Make sure to cover the sensor with the entirety of your finger.
<small><i>The screening questionnaire is only meant as an aid and cannot diagnose you.
Consult a health care provider if you have medical questions.</i></small>
"""
TemperaturePrompt = """
We will ask a series of daily screening Questions to protect from
exposure during the COVID-19 pandemic and provide a safe environment

<small><i>The screening questionnaire is only meant as an aid and cannot diagnose you.
Consult a health care provider if you have medical questions.</i></small>
"""
FirstPrompt = """\n\n
<span weight="bold" size="40000">COVID SCREENING CHECKPOINT</span>
"""
start_screening_msg = """Hover your hand over any two sensors on the Left/Right side to start! \rKeep your hand very close to the sensor and hold steady until\r selection is confirmed.\r"""



RFIDPrompt = """\n\n\n\n\n
<span weight="bold" size="40000">COVID SCREENING CHECKPOINT</span>
\n\n
<span size="x-large">Please Scan your ID Card</span>
"""

CardSuccessPrompt = """\n\n\n\n\n
<span weight="bold" size="40000">COVID SCREENING CHECKPOINT</span>
\n\n
<span weight="bold" size="x-large" foreground="#009900">Card successfully detected</span>
"""

CardFailPrompt = """\n\n\n\n\n
<span weight="bold" size="40000">COVID SCREENING CHECKPOINT</span>
\n\n
<span weight="bold" foreground="red" size="x-large">Card not recognized. Please try again!</span>
"""

AdminPrompt = """
<span weight="bold" size="25000">Admin Key Card was detected! Admin Mode Enabled.</span>
<span size="22000">Use the two sensors on the sides to make the following decisions:</span>
<span weight="bold" size="22000" foreground="#5163bd"> 1:  To Add/Remove users, use the Right Sensor </span>
<span weight="bold" size="22000" foreground="#bd518e"> 2:  To Configure device Features, use the Left Sensor </span>
<span weight="bold" size="22000" foreground="#bd8c51"> 3:  To Safely Shutdown the system, use both Sensors </span>
To exit Admin Mode, re-tap the Admin Key Card.
"""

AddRemoveUserPrompt = """
<span weight="bold" size="25000">Add/Remove users selected:</span>\n
<span size="22000">Use the two sensors on the sides to make the following decisions:</span>
<span weight="bold" size="22000">Right Sensor:  To Add a new user </span>
<span weight="bold" size="22000">Left Sensor:  To Remove an old user </span>

"""

NewUserPrompt = """\n\n\n
<span weight="bold" size="33000">Please tap a new key card to register a new user</span>
\n\n\n
"""

NewUserPrompt2 = """\n\n\n
<span weight="bold" size="33000">Please tap a new key card to register a new user</span>
\n
<span weight="bold" size="x-large" foreground="#009900">New key card successfully detected!</span>
"""

NewUserPrompt3 = """\n\n\n
<span weight="bold" size="33000">Please tap a new key card to register a new user</span>
\n
<span weight="bold" size="large" foreground="red">Registeration Failed! This key card is already registered!</span>
"""

RemoveUserPrompt = """\n\n\n
<span weight="bold" size="30000">Please tap the key card to remove the user from the system</span>
\n\n\n
"""

RemoveUserPrompt2 = """\n\n\n
<span weight="bold" size="30000">Please tap the key card to remove the user from the system</span>
\n
<span weight="bold" size="large" foreground="#009900">User Successfully Removed!</span>
"""
RemoveUserPrompt3 = """\n\n\n
<span weight="bold" size="30000">Please tap the key card to remove the user from the system</span>
\n
<span weight="bold" size="large" foreground="red">Failure! This key card is not registered in the system</span>
"""

FeaturesPrompt = ("""<i>1/5</i>

<b> Do you want Key Card Access Enabled? </b> 
""", """<i>2/5</i>

<b> Do you want Face Mask Detection Enabled? </b>
        
""","""<i>3/5</i>

<b> Do you want Temperature Screening Enabled? </b> 
""","""<i>4/5</i>                   

<b> Do you want SpO2 Measurement Enabled? </b> 
""","""<i>5/5</i>

<b> Do you want COVID Screening Questionnaire Enabled? </b> 
""")

YesNoWarn = """Hover your hand over the Right Sensor for "Yes" and Left Sensor for "No".\rKeep your hand very close to the sensor and hold steady until\rthe selection is confirmed.\r"""
