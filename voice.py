#!/usr/bin/env python3
import os
import sys
import wave
import struct


def get_arguments():
    if len(sys.argv) < 2:
        print("No VOC file specified.")
        sys.exit(-1)

    filename = sys.argv[1]
    if not os.path.isfile(filename):
        print("Not a valid file \"{}\".".format(filename))
        sys.exit(-1)
    return os.path.abspath(filename)


def convert_voice(filename):
    handle = open(filename, 'rb')
    
    try:
        magic_bytes = handle.read(19)
        magic_a = magic_bytes.decode('utf-8', errors='ignore')
    except Exception:
        handle.seek(0)
        dump_wave(filename, 22050, 1, handle.read())
        handle.close()
        return

    if magic_a != "Creative Voice File":
        handle.seek(0)
        dump_wave(filename, 22050, 1, handle.read())
        handle.close()
        return

    magic_b = handle.read(1)
    if not magic_b or magic_b[0] != 0x1A:
        handle.seek(0)
        dump_wave(filename, 22050, 1, handle.read())
        handle.close()
        return

    handle.read(6)

    while True:
        block_type_byte = handle.read(1)
        if not block_type_byte:
            break
        block_type = block_type_byte[0]
        
        if block_type == 0:
            break

        size_bytes = handle.read(3)
        if len(size_bytes) < 3:
            break
        
        block_size = size_bytes[0] + (size_bytes[1] << 8) + (size_bytes[2] << 16)

        if block_type == 1:
            freq_div_byte = handle.read(1)
            codec_id_byte = handle.read(1)
            if not freq_div_byte or not codec_id_byte:
                break
                
            freq_div = freq_div_byte[0]
            codec_id = codec_id_byte[0]
            
            if freq_div >= 256:
                freq_div = 211
            sample_rate = int(1000000 / (256 - freq_div))
            channel_count = 1 
            
            audio_data_size = block_size - 2
            audio_data = handle.read(audio_data_size)
            
            if codec_id == 0: 
                dump_wave(filename, sample_rate, channel_count, audio_data)

        elif block_type == 9:
            header_data = handle.read(12)
            if len(header_data) < 12:
                break
                
            sample_rate = struct.unpack('<I', header_data[0:4])[0]
            sample_bits = header_data[4]
            channel_count = header_data[5]
            codec_id = struct.unpack('<H', header_data[6:8])[0]
            
            audio_data_size = block_size - 12
            audio_data = handle.read(audio_data_size)
            
            if sample_bits == 8 and codec_id == 0: 
                dump_wave(filename, sample_rate, channel_count, audio_data)
            
        else:
            handle.read(block_size)

    handle.close()


def dump_wave(filename, rate, channels, data):
    out_name = os.path.splitext(filename)[0] + ".wav"
    if not data:
        return
        
    if os.path.exists(out_name):
        print("  -> Overwriting sound effect: {}".format(os.path.basename(out_name)))
    else:
        print("  -> Creating sound effect: {}".format(os.path.basename(out_name)))

    wav = wave.open(out_name, 'wb')
    wav.setsampwidth(1) 
    wav.setnchannels(channels)
    wav.setframerate(rate)
    wav.writeframes(data)
    wav.close()


def main():
    filename = get_arguments()
    convert_voice(filename)


if __name__ == "__main__":
    main()
