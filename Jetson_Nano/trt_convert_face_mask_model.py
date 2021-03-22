from tensorflow.python.compiler.tensorrt import trt_convert as trt

print('Converting to TF-TRT FP16...')
conversion_params = trt.DEFAULT_TRT_CONVERSION_PARAMS._replace(
    precision_mode=trt.TrtPrecisionMode.FP16)
 #   max_workspace_size_bytes=3000000000)
converter = trt.TrtGraphConverterV2(
   input_saved_model_dir='face_mask_detection_model', conversion_params=conversion_params)
converter.convert()
converter.save(output_saved_model_dir='face_mask_detection_model_TFTRT_FP16')
print('Done Converting to TF-TRT FP16')

