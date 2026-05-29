#!/usr/bin/env python3
import os
import sys
import png
import struct


def get_arguments():
    if len(sys.argv) < 2:
        print("No FNT file specified.")
        sys.exit(-1)
    filename = sys.argv[1]
    if not os.path.isfile(filename):
        print("Not a valid file \"{}\".".format(filename))
        sys.exit(-1)

    if len(sys.argv) < 3:
        print("No PAL file specified.")
        sys.exit(-1)
    palfile = sys.argv[2]
    if not os.path.isfile(palfile):
        print("Not a valid palette file \"{}\".".format(palfile))
        sys.exit(-1)
    
    with open(palfile, 'rb') as f:
        palette = read_palette(f)

    return os.path.abspath(filename), palette


def extract_characters(filename, pal):
    try:
        handle = open(filename, 'rb')
        magic = struct.unpack('<I', handle.read(4))[0]
        
        if magic != 0x00002e31:
            print("  [Skipped] {} (Invalid FNT signature).".format(os.path.basename(filename)))
            handle.close()
            return

        character_count = struct.unpack('<I', handle.read(4))[0]
        character_height = struct.unpack('<I', handle.read(4))[0]
        color_transparent = struct.unpack('<I', handle.read(4))[0]
    except Exception as e:
        print("  [Error] Could not read header of {}: {}".format(os.path.basename(filename), e))
        return

    if color_transparent < len(pal):
        pal[color_transparent][3] = 0x00

    dir_path, file_ = os.path.split(os.path.abspath(filename))
    folder_name = file_.replace('.fnt', '').replace('.FNT', '')
    dir_path = os.path.join(dir_path, folder_name)
    
    os.makedirs(dir_path, exist_ok=True)
    
    print("Processing font {} (Characters: {})...".format(file_, character_count))

    for i in range(character_count):
        try:
            off_char = struct.unpack('<I', handle.read(4))[0]
            off_restore = handle.tell()
            handle.seek(off_char)
            fnt_to_png(dir_path, pal, handle, i, character_height)
            handle.seek(off_restore)
        except Exception:
            continue
            
    handle.close()


def read_palette(handle, size=256):
    entries = []
    eof_reached = False
    
    for index in range(size):
        if not eof_reached:
            rgb = handle.read(3)
            if len(rgb) < 3:
                # File ended early, trigger warning and fill remaining slots
                print("  [Warning] Palette file ended prematurely at index {}.".format(index), file=sys.stderr)
                eof_reached = True
        
        if eof_reached:
            # Safe fallback: fill missing colors with solid black (or transparent [0,0,0,0])
            entries.append([0, 0, 0, 0xFF])
        else:
            entries.append([rgb[0] << 2, rgb[1] << 2, rgb[2] << 2, 0xFF])
            
    return entries


def fnt_to_png(dir_path, palette, handle, entry, height):
    pngstr = "{:02X}.png".format(entry)
    filename = os.path.join(dir_path, pngstr)

    try:
        width = struct.unpack('<I', handle.read(4))[0]
        if not width:
            return
    except Exception:
        return

    def row_generator():
        for y in range(height):
            row = []
            for x in range(width):
                byte_data = handle.read(1)
                if not byte_data:
                    palette_index = 0
                else:
                    palette_index = byte_data[0]
                
                color = palette[palette_index] if palette_index < len(palette) else [0, 0, 0, 0]
                row.extend(color)
            yield row

    with open(filename, 'wb') as fout:
        w = png.Writer(width=width, height=height, bitdepth=8, greyscale=False, alpha=True)
        w.write(fout, row_generator())


def main():
    filename, palette = get_arguments()
    extract_characters(filename, palette)


if __name__ == "__main__":
    main()
