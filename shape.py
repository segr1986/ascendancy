#!/usr/bin/env python3
import os
import sys
import png
import struct

def get_arguments():
    if len(sys.argv) < 2:
        print("Usage: python3 shape.py <file.shp> [palette.pal]", file=sys.stderr)
        sys.exit(-1)
    
    filename = os.path.abspath(sys.argv[1])
    palette = None
    
    if len(sys.argv) == 3:
        palfile = sys.argv[2]
        with open(palfile, 'rb') as f:
            palette = read_palette(f)
    
    return filename, palette

def read_palette(handle, size=256):
    entries = []
    for _ in range(size):
        rgb = handle.read(3)
        if len(rgb) < 3:
            entries.append([0, 0, 0, 0xFF])
        else:
            entries.append([rgb[0] << 2, rgb[1] << 2, rgb[2] << 2, 0xFF])
    return entries

def parse_shp(filename, global_palette):
    with open(filename, 'rb') as handle:
        magic = struct.unpack('<I', handle.read(4))[0]
        if magic != 0x30312E31:
            print("Error: Invalid Ascendancy signature.", file=sys.stderr)
            sys.exit(-1)
        
        image_count = struct.unpack('<I', handle.read(4))[0]
        offsets = []
        for _ in range(image_count):
            off_dat = struct.unpack('<I', handle.read(4))[0]
            off_pal = struct.unpack('<I', handle.read(4))[0]
            offsets.append((off_dat, off_pal))
        
        frames = []
        file_size = os.path.getsize(filename)
        sorted_dat_offsets = sorted([o[0] for o in offsets])
        
        for i, (off_dat, off_pal) in enumerate(offsets):
            current_palette = global_palette
            if off_pal != 0:
                origin = handle.tell()
                handle.seek(off_pal)
                current_palette = read_palette(handle)
                handle.seek(origin)
            elif global_palette is None:
                current_palette = [[g, g, g, 0xFF] for g in range(256)]
            
            handle.seek(off_dat)
            height   = struct.unpack('<H', handle.read(2))[0] + 1
            width    = struct.unpack('<H', handle.read(2))[0] + 1
            x_center = struct.unpack('<H', handle.read(2))[0]
            y_center = struct.unpack('<H', handle.read(2))[0]
            
            x_start  = struct.unpack('<i', handle.read(4))[0]
            y_start  = struct.unpack('<i', handle.read(4))[0]
            x_end    = struct.unpack('<i', handle.read(4))[0]
            y_end    = struct.unpack('<i', handle.read(4))[0]
            
            next_offset = file_size
            idx_in_sorted = sorted_dat_offsets.index(off_dat)
            if idx_in_sorted + 1 < len(sorted_dat_offsets):
                next_offset = sorted_dat_offsets[idx_in_sorted + 1]
            
            rle_len = next_offset - (off_dat + 28)
            if rle_len < 0: 
                rle_len = 0 
            
            rle_data = handle.read(rle_len)
            
            frames.append({
                "num": i + 1, "width": width, "height": height,
                "x_center": x_center, "y_center": y_center,
                "x_start": x_start, "y_start": y_start,
                "x_end": x_end, "y_end": y_end,
                "palette": current_palette, "rle_data": rle_data
            })
    return frames, image_count

def decompress_rle(frame, transparent):
    w, h = frame["width"], frame["height"]
    buf = [[transparent for _ in range(w)] for _ in range(h)]
    rle = frame["rle_data"]
    data_len = len(rle)
    idx = 0
    
    x, y = 0, 0
    just_auto_wrapped = False
    
    while y < h and idx < data_len:
        b = rle[idx]
        idx += 1
        
        if b == 0:
            if (x > 0 or y > 0) and not just_auto_wrapped:
                y += 1
                x = 0
            just_auto_wrapped = False
            continue
        
        if idx >= data_len: 
            break
        
        just_auto_wrapped = False
        
        if b == 1:
            skip = rle[idx]
            idx += 1
            for _ in range(skip):
                x += 1
                if x >= w:
                    y += 1
                    x = 0
                    just_auto_wrapped = True
        
        elif (b & 1) == 0:
            count = b >> 1
            pal_idx = rle[idx]
            idx += 1
            clr = frame["palette"][pal_idx] if pal_idx < 256 else transparent
            for _ in range(count):
                if y < h and x < w:
                    buf[y][x] = clr
                x += 1
                if x >= w:
                    y += 1
                    x = 0
                    just_auto_wrapped = True
                else:
                    just_auto_wrapped = False
        
        else:
            count = b >> 1
            for _ in range(count):
                if idx >= data_len: break
                pal_idx = rle[idx]
                idx += 1
                clr = frame["palette"][pal_idx] if pal_idx < 256 else transparent
                if y < h and x < w:
                    buf[y][x] = clr
                x += 1
                if x >= w:
                    y += 1
                    x = 0
                    just_auto_wrapped = True
                else:
                    just_auto_wrapped = False
                
    return buf

def write_png(filename, width, height, grid):
    pixels = [[pixel for rgba in row for pixel in rgba] for row in grid]
    with open(filename, 'wb') as fout:
        w = png.Writer(width=width, height=height, bitdepth=8, greyscale=False, alpha=True)
        w.write(fout, pixels)

def pipeline_render(frame, raw_buf, output_dir, total_count, transparent):
    z_num = str(frame['num']).zfill(len(str(total_count)))
    base_path = os.path.join(output_dir, z_num)
    
    canvas_w = frame["width"]
    canvas_height = frame["height"]
    
    if frame["x_end"] == frame["x_start"]:
        offset_x = 0
    else:
        offset_x = frame["x_center"] + frame["x_start"]
    
    actual_content_height = frame["y_end"] - frame["y_start"] + 1
    offset_y = canvas_height - actual_content_height
    
    if offset_x < 0 or offset_x >= canvas_w: offset_x = 0
    if offset_y < 0 or offset_y >= canvas_height: offset_y = 0
    
    engine_grid = [[transparent for _ in range(canvas_w)] for _ in range(canvas_height)]
    
    for y in range(canvas_height):
        dst_y = y + offset_y
        if 0 <= dst_y < canvas_height:
            for x in range(canvas_w):
                dst_x = x + offset_x
                if 0 <= dst_x < canvas_w:
                    engine_grid[dst_y][dst_x] = raw_buf[y][x]
    
    #write_png(f"{base_path}_raw.png", canvas_w, canvas_height, raw_buf)
    write_png(f"{base_path}.png", canvas_w, canvas_height, engine_grid)

def main():
    filename, palette = get_arguments()
    output_dir = os.path.join(os.path.dirname(filename), os.path.splitext(os.path.basename(filename))[0].lower())
    os.makedirs(output_dir, exist_ok=True)
    
    transparent = [0, 0, 0, 0x00]
    frames, total_count = parse_shp(filename, palette)
    
    for frame in frames:
        raw_buf = decompress_rle(frame, transparent)
        pipeline_render(frame, raw_buf, output_dir, total_count, transparent)
    
    print(f"Pipeline executed successfully for {filename}")

if __name__ == "__main__":
    main()

