"""
Media processing domain templates for NLP2CMD.

Contains ImageMagick, sox, media file management templates.
"""

MEDIA_TEMPLATES = {
    # ImageMagick — convert
    'img_convert': "convert {input} {output}",
    'img_resize': "convert {input} -resize {width}x{height} {output}",
    'img_resize_percent': "convert {input} -resize {percent}% {output}",
    'img_crop': "convert {input} -crop {width}x{height}+{x}+{y} {output}",
    'img_rotate': "convert {input} -rotate {degrees} {output}",
    'img_flip': "convert {input} -flip {output}",
    'img_flop': "convert {input} -flop {output}",
    'img_quality': "convert {input} -quality {quality} {output}",
    'img_grayscale': "convert {input} -colorspace Gray {output}",
    'img_sepia': "convert {input} -sepia-tone 80% {output}",
    'img_blur': "convert {input} -blur 0x{radius} {output}",
    'img_sharpen': "convert {input} -sharpen 0x{radius} {output}",
    'img_brightness': "convert {input} -brightness-contrast {brightness}x{contrast} {output}",
    'img_thumbnail': "convert {input} -thumbnail {width}x{height} {output}",
    'img_watermark': "composite -dissolve {opacity} -gravity {gravity} {watermark} {input} {output}",
    'img_text': "convert {input} -pointsize {size} -fill {color} -annotate +{x}+{y} '{text}' {output}",
    'img_border': "convert {input} -border {size} -bordercolor '{color}' {output}",
    'img_strip_metadata': "convert {input} -strip {output}",
    'img_info': "identify -verbose {input}",
    'img_format': "identify -format '%wx%h %m %b' {input}",
    # ImageMagick — batch
    'img_batch_resize': "mogrify -resize {width}x{height} *.{extension}",
    'img_batch_convert': "mogrify -format {format} *.{extension}",
    'img_batch_quality': "mogrify -quality {quality} *.{extension}",
    'img_montage': "montage *.{extension} -tile {cols}x{rows} -geometry +{gap}+{gap} {output}",
    'img_sprite': "convert *.{extension} +append {output}",
    # PDF operations
    'pdf_to_images': "convert -density {dpi} {input} {output_pattern}",
    'images_to_pdf': "convert *.{extension} {output}",
    'pdf_merge': "pdfunite {input_files} {output}",
    'pdf_split': "pdfseparate {input} {output_pattern}",
    'pdf_info': "pdfinfo {input}",
    'pdf_to_text': "pdftotext {input} {output}",
    # Sox — audio
    'sox_convert': "sox {input} {output}",
    'sox_trim': "sox {input} {output} trim {start} {duration}",
    'sox_concat': "sox {input_files} {output}",
    'sox_volume': "sox -v {volume} {input} {output}",
    'sox_reverse': "sox {input} {output} reverse",
    'sox_speed': "sox {input} {output} speed {factor}",
    'sox_info': "soxi {input}",
    'sox_normalize': "sox --norm {input} {output}",
    'sox_mix': "sox -m {input1} {input2} {output}",
    # exiftool
    'exif_show': "exiftool {input}",
    'exif_strip': "exiftool -all= {input}",
    'exif_set': "exiftool -{tag}='{value}' {input}",
    'exif_gps': "exiftool -gpslatitude -gpslongitude {input}",
}
