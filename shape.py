#!/usr/bin/env python3
import os
import sys
import png
import struct


def get_arguments():
    if len(sys.argv) < 2:
        print("No SHP file specified.")
        sys.exit(-1)
    filename = sys.argv[1]
    if not os.path.isfile(filename):
        print("Not a valid file \"{}\".".format(filename))
        sys.exit(-1)

    palette = None
    if len(sys.argv) == 3:
        palfile = sys.argv[2]
        if not os.path.isfile(palfile):
            print("Not a valid palette file \"{}\".".format(palfile))
            sys.exit(-1)
        palfile = open(palfile, 'rb')
        palette = read_palette(palfile)
        palfile.close()

    return os.path.abspath(filename), palette


def extract_shapes(filename, pal0):
    try:
        handle = open(filename, 'rb')
        magic = struct.unpack('<I', handle.read(4))[0]
        
        if magic != 0x30312E31:
            print("  [Skipped] {} (Invalid Ascendancy signature).".format(os.path.basename(filename)))
            handle.close()
            return
            
        image_count = struct.unpack('<I', handle.read(4))[0]
    except Exception as e:
        print("  [Error] Could not open {}: {}".format(os.path.basename(filename), e))
        return

    dir, file_ = os.path.split(os.path.abspath(filename))
    folder_name = file_.replace('.shp', '').replace('.SHP', '')
    dir = os.path.join(dir, folder_name)
    
    os.makedirs(dir, exist_ok=True)
    
    offsets = []
    for i in range(image_count):
        off_dat = struct.unpack('<I', handle.read(4))[0]
        off_pal = struct.unpack('<I', handle.read(4))[0]
        offsets.append((off_dat, off_pal))
    
    print("Processing {} (Images: {})...".format(file_, image_count))
    
    for i in range(image_count):
        off_dat, off_pal = offsets[i]

        palette = pal0
        if off_pal != 0:
            handle.seek(off_pal)
            palette = read_palette(handle)
        elif pal0 is None:
            palette = [[g, g, g, 0xFF] for g in range(256)]

        handle.seek(off_dat)
        shp_to_png(dir, palette, handle, i+1, image_count)
        
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


def shp_to_png(dir, palette, handle, entry, total):
    idxlen = len("{}".format(total))
    pngstr = "{}".format(entry).rjust(idxlen, '0')
    pngstr = "".join([pngstr, '.png'])
    filename = os.path.join(dir, pngstr)

    try:
        height = 1 + struct.unpack('<H', handle.read(2))[0]
        width = 1 + struct.unpack('<H', handle.read(2))[0]
        
        x_center = struct.unpack('<H', handle.read(2))[0]
        y_center = struct.unpack('<H', handle.read(2))[0]
        x_start  = struct.unpack('<i', handle.read(4))[0]
        y_start  = struct.unpack('<i', handle.read(4))[0]
        x_end    = struct.unpack('<i', handle.read(4))[0]
        y_end    = struct.unpack('<i', handle.read(4))[0]
    except:
        print("Unable to read header for image {}.".format(entry))
        return

    transparent_pixel = [0, 0, 0, 0]
    pixel_grid = [[transparent_pixel for _ in range(width)] for _ in range(height)]
    
    x = 0
    y = 0

    total_data_rows = y_end - y_start
    rows_processed = 0

    pixels_written_in_row = False

    while y < height and rows_processed <= total_data_rows:
        byte_data = handle.read(1)
        if not byte_data:
            break

        b = byte_data[0]

        if b == 0:
            if pixels_written_in_row:
                y += 1
                rows_processed += 1
            x = 0
            pixels_written_in_row = False
            continue
            
        elif b == 1:
            skip_data = handle.read(1)
            if not skip_data:
                break
            x += skip_data[0]
            
        elif (b & 1) == 0:
            count = b >> 1
            pal_data = handle.read(1)
            if not pal_data:
                break
            pal_idx = pal_data[0]
            clr = palette[pal_idx] if pal_idx < len(palette) else transparent_pixel
            
            for _ in range(count):
                if 0 <= y < height and 0 <= x < width:
                    pixel_grid[y][x] = clr
                    pixels_written_in_row = True
                x += 1
        else:
            count = b >> 1
            for _ in range(count):
                pal_data = handle.read(1)
                if not pal_data:
                    break
                pal_idx = pal_data[0]
                clr = palette[pal_idx] if pal_idx < len(palette) else transparent_pixel
                
                if 0 <= y < height and 0 <= x < width:
                    pixel_grid[y][x] = clr
                    pixels_written_in_row = True
                x += 1

        if x >= width:
            if pixels_written_in_row:
                y += 1
                rows_processed += 1
            x = 0
            pixels_written_in_row = False

    pixels = []
    for r in range(height):
        row = []
        for c in range(width):
            row += pixel_grid[r][c]
        pixels.append(row)

    with open(filename, 'wb') as fout:
        w = png.Writer(width=width, height=height, bitdepth=8, greyscale=False, alpha=True)
        w.write(fout, pixels)


def main():
    filename, palette = get_arguments()
    extract_shapes(filename, palette)


if __name__ == "__main__":
    main()
