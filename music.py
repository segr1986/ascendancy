#!/usr/bin/env python3
import os
import sys
import wave


def get_arguments():
    if len(sys.argv) < 2:
        print("No RAW file specified.")
        print("Usage: python3 music.py FILE.RAW")
        sys.exit(-1)
    
    filename = sys.argv[1]
    if not os.path.isfile(filename):
        print("Not a valid file \"{}\".".format(filename))
        sys.exit(-1)
    return os.path.abspath(filename)


def convert_raw_music(filename):
    out_name = os.path.splitext(filename)[0] + ".wav"
    
    try:
        with open(filename, "rb") as f:
            raw_audio_data = f.read()

        if not raw_audio_data:
            return

        if os.path.exists(out_name):
            print("  -> Overwriting music track: {}".format(os.path.basename(out_name)))
        else:
            print("  -> Creating music track: {}".format(os.path.basename(out_name)))

        wav = wave.open(out_name, "wb")
        wav.setsampwidth(1)
        wav.setnchannels(1)
        wav.setframerate(22050)
        wav.writeframes(raw_audio_data)
        wav.close()

    except Exception as e:
        print("  [Error] Could not convert {}: {}".format(os.path.basename(filename), e), file=sys.stderr)


def main():
    filename = get_arguments()
    convert_raw_music(filename)


if __name__ == "__main__":
    main()
