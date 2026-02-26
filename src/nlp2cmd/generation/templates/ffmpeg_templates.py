"""
FFmpeg domain templates for NLP2CMD.

Contains video/audio conversion, streaming, media processing templates.
"""

FFMPEG_TEMPLATES = {
    # Video conversion
    'convert': "ffmpeg -i {input} {output}",
    'convert_format': "ffmpeg -i {input} -c:v {video_codec} -c:a {audio_codec} {output}",
    'convert_mp4': "ffmpeg -i {input} -c:v libx264 -c:a aac {output}",
    'convert_webm': "ffmpeg -i {input} -c:v libvpx-vp9 -c:a libopus {output}",
    'convert_avi': "ffmpeg -i {input} -c:v mpeg4 -c:a mp3 {output}",
    'convert_mkv': "ffmpeg -i {input} -c copy {output}",
    'convert_gif': "ffmpeg -i {input} -vf 'fps={fps},scale={width}:-1:flags=lanczos' {output}",
    # Video operations
    'trim': "ffmpeg -i {input} -ss {start} -to {end} -c copy {output}",
    'cut': "ffmpeg -i {input} -ss {start} -t {duration} -c copy {output}",
    'concat': "ffmpeg -f concat -safe 0 -i {filelist} -c copy {output}",
    'merge_audio_video': "ffmpeg -i {video} -i {audio} -c:v copy -c:a aac {output}",
    'extract_audio': "ffmpeg -i {input} -vn -c:a {audio_codec} {output}",
    'extract_audio_mp3': "ffmpeg -i {input} -vn -c:a libmp3lame -q:a 2 {output}",
    'remove_audio': "ffmpeg -i {input} -an -c:v copy {output}",
    'add_subtitles': "ffmpeg -i {input} -vf subtitles={subtitle_file} {output}",
    'add_watermark': "ffmpeg -i {input} -i {watermark} -filter_complex 'overlay={x}:{y}' {output}",
    # Resize / Scale
    'resize': "ffmpeg -i {input} -vf scale={width}:{height} {output}",
    'resize_720p': "ffmpeg -i {input} -vf scale=-1:720 -c:v libx264 -c:a copy {output}",
    'resize_1080p': "ffmpeg -i {input} -vf scale=-1:1080 -c:v libx264 -c:a copy {output}",
    'resize_4k': "ffmpeg -i {input} -vf scale=-1:2160 -c:v libx264 -c:a copy {output}",
    # Compression
    'compress': "ffmpeg -i {input} -c:v libx264 -crf {crf} -c:a aac -b:a 128k {output}",
    'compress_light': "ffmpeg -i {input} -c:v libx264 -crf 23 -preset fast {output}",
    'compress_heavy': "ffmpeg -i {input} -c:v libx264 -crf 28 -preset slow -c:a aac -b:a 96k {output}",
    # Audio
    'audio_convert': "ffmpeg -i {input} -c:a {codec} {output}",
    'audio_mp3': "ffmpeg -i {input} -c:a libmp3lame -q:a 2 {output}",
    'audio_wav': "ffmpeg -i {input} -c:a pcm_s16le {output}",
    'audio_ogg': "ffmpeg -i {input} -c:a libvorbis {output}",
    'audio_flac': "ffmpeg -i {input} -c:a flac {output}",
    'audio_bitrate': "ffmpeg -i {input} -c:a libmp3lame -b:a {bitrate} {output}",
    'audio_normalize': "ffmpeg -i {input} -af loudnorm {output}",
    'audio_volume': "ffmpeg -i {input} -af volume={volume} {output}",
    'audio_fade': "ffmpeg -i {input} -af afade=t=in:st=0:d={fade_in},afade=t=out:st={fade_out_start}:d={fade_out} {output}",
    # Screenshots / Thumbnails
    'screenshot': "ffmpeg -i {input} -ss {time} -vframes 1 {output}",
    'thumbnails': "ffmpeg -i {input} -vf fps=1/{interval} {output_pattern}",
    'thumbnail_grid': "ffmpeg -i {input} -vf 'select=not(mod(n\\,{interval})),scale={width}:-1,tile={cols}x{rows}' -frames:v 1 {output}",
    # Info
    'info': "ffprobe -v quiet -print_format json -show_format -show_streams {input}",
    'duration': "ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 {input}",
    'resolution': "ffprobe -v error -select_streams v:0 -show_entries stream=width,height -of csv=s=x:p=0 {input}",
    # Streaming
    'stream_rtmp': "ffmpeg -re -i {input} -c copy -f flv {rtmp_url}",
    'stream_hls': "ffmpeg -i {input} -codec copy -start_number 0 -hls_time {segment_time} -hls_list_size 0 -f hls {output}",
    'record_screen': "ffmpeg -f x11grab -s {resolution} -i :0.0 -c:v libx264 -preset ultrafast {output}",
    'record_webcam': "ffmpeg -f v4l2 -i /dev/video0 -c:v libx264 {output}",
    # Batch
    'batch_convert': "for f in *.{input_ext}; do ffmpeg -i \"$f\" \"${{f%.{input_ext}}}.{output_ext}\"; done",
    'speed_up': "ffmpeg -i {input} -filter:v 'setpts={speed}*PTS' -filter:a 'atempo={audio_speed}' {output}",
    'slow_down': "ffmpeg -i {input} -filter:v 'setpts={speed}*PTS' -filter:a 'atempo={audio_speed}' {output}",
    'rotate': "ffmpeg -i {input} -vf 'transpose={direction}' {output}",
    'flip_horizontal': "ffmpeg -i {input} -vf hflip {output}",
    'flip_vertical': "ffmpeg -i {input} -vf vflip {output}",
}
