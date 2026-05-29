#!/usr/bin/env python3
import os
import sys
import shutil
import subprocess


def get_arguments():
    if len(sys.argv) < 3:
        print("Error: Missing parameters.")
        print("Usage: python3 extract_all.py /path/to/cd/drive /path/to/target")
        sys.exit(-1)
        
    cd_path = os.path.abspath(sys.argv[1])
    target_path = os.path.abspath(sys.argv[2])
    
    if not os.path.isdir(cd_path):
        print("Error: CD path '{}' is not a valid directory.".format(cd_path))
        sys.exit(-1)
        
    return cd_path, target_path


def run_tool(script_name, args):
    script_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), script_name)
    if not os.path.isfile(script_path):
        print("  [Warning] Tool '{}' not found.".format(script_name))
        return False
    
    cmd = ["python3", script_path] + args
    result = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    return result.returncode == 0


def main():
    cd_path, target_path = get_arguments()
    
    cob_files = ["ASCEND00.COB", "ASCEND01.COB", "ASCEND02.COB"]
    found_cobs = []
    
    for cob in cob_files:
        p = os.path.join(cd_path, cob)
        if not os.path.isfile(p):
            p = os.path.join(cd_path, cob.lower())
        if os.path.isfile(p):
            found_cobs.append(p)

    if not found_cobs:
        print("Error: No Ascendancy COB files found on the specified CD path.")
        sys.exit(-1)

    graphics_dir = os.path.join(target_path, "graphics")
    interface_dir = os.path.join(target_path, "interface")
    fonts_dir = os.path.join(target_path, "fonts")
    sfx_dir = os.path.join(target_path, "sfx")
    music_dir = os.path.join(target_path, "music")
    data_dir = os.path.join(target_path, "data")
    shading_dir = os.path.join(target_path, "shading")
    ai_logic_dir = os.path.join(target_path, "ai_logic")

    tmp_base = os.path.join(target_path, "__tmp_extract__")
    os.makedirs(tmp_base, exist_ok=True)

    print("=== STARTING MASTER ASSET INGESTION ===")
    
    print("\n[1/5] Extracting archives to isolated workspaces...")
    for cob_path in found_cobs:
        cob_name = os.path.splitext(os.path.basename(cob_path))[0].lower()
        cob_tmp_dir = os.path.join(tmp_base, cob_name)
        os.makedirs(cob_tmp_dir, exist_ok=True)
        
        print("  -> Unpacking: {} into workspace '{}'".format(os.path.basename(cob_path), cob_name))
        run_tool("cob.py", [cob_path, cob_tmp_dir])

    print("\n[2/5] Locating master color palettes...")
    game_pal = None
    font_pal = None
    
    for root, _, files in os.walk(tmp_base):
        for f in files:
            f_low = f.lower()
            if f_low == "game.pal" and not game_pal:
                game_pal = os.path.join(root, f)
                print("  [Found] In-game palette located: game.pal")
            elif f_low == "subfont.pal" and not font_pal:
                font_pal = os.path.join(root, f)
                print("  [Found] Typography palette located: subfont.pal")

    # Fallback falls subfont.pal fehlt
    if not font_pal:
        font_pal = game_pal

    print("\n[3/5] Converting asset binaries...")
    for root, dirs, files in os.walk(tmp_base):
        for file in files:
            file_lower = file.lower()
            full_file_path = os.path.join(root, file)
            
            if file_lower.endswith(".shp") or file_lower.endswith(".tmp"):
                if file_lower.endswith(".tmp"):
                    print("  [Converting TMP as Interface SHP] {}".format(file))
                    shp_fallback_path = full_file_path + ".shp"
                    os.rename(full_file_path, shp_fallback_path)
                    run_tool("shape.py", [shp_fallback_path, game_pal] if game_pal else [shp_fallback_path])
                    generated_folder = shp_fallback_path[:-4]
                    current_dest_dir = interface_dir
                else:
                    print("  [Converting SHP] {}".format(file))
                    run_tool("shape.py", [full_file_path, game_pal] if game_pal else [full_file_path])
                    generated_folder = full_file_path[:-4]
                    current_dest_dir = graphics_dir
                    
                if os.path.isdir(generated_folder):
                    os.makedirs(current_dest_dir, exist_ok=True)
                    dest_folder = os.path.join(current_dest_dir, os.path.basename(generated_folder))
                    if os.path.exists(dest_folder):
                        shutil.rmtree(dest_folder)
                    shutil.move(generated_folder, current_dest_dir)

            elif file_lower.endswith(".fnt"):
                # We enforce font_pal (subfont.pal) for typography, or look for local context
                selected_font_pal = font_pal
                for f in files:
                    if f.lower().endswith(".pal") and f.lower() != "game.pal":
                        selected_font_pal = os.path.join(root, f)
                        break
                
                print("  [Converting FNT] {} using palette {}".format(file, os.path.basename(selected_font_pal)))
                run_tool("font.py", [full_file_path, selected_font_pal])
                generated_folder = full_file_path[:-4]
                if os.path.isdir(generated_folder):
                    os.makedirs(fonts_dir, exist_ok=True)
                    dest_folder = os.path.join(fonts_dir, os.path.basename(generated_folder))
                    if os.path.exists(dest_folder):
                        shutil.rmtree(dest_folder)
                    shutil.move(generated_folder, fonts_dir)

            elif file_lower.endswith(".voc"):
                print("  [Converting VOC] {}".format(file))
                run_tool("voice.py", [full_file_path])
                generated_wav = full_file_path[:-4] + ".wav"
                if os.path.isfile(generated_wav):
                    os.makedirs(sfx_dir, exist_ok=True)
                    shutil.move(generated_wav, os.path.join(sfx_dir, os.path.basename(generated_wav)))

            elif file_lower.endswith(".raw"):
                print("  [Converting RAW] {}".format(file))
                run_tool("music.py", [full_file_path])
                generated_wav = full_file_path[:-4] + ".wav"
                if os.path.isfile(generated_wav):
                    os.makedirs(music_dir, exist_ok=True)
                    shutil.move(generated_wav, os.path.join(music_dir, os.path.basename(generated_wav)))

    print("\n[4/5] Sorting text databases and remaining game scripts...")
    os.makedirs(data_dir, exist_ok=True)
    os.makedirs(ai_logic_dir, exist_ok=True)
    os.makedirs(shading_dir, exist_ok=True)
    
    for root, _, files in os.walk(tmp_base):
        for file in files:
            file_lower = file.lower()
            src_file = os.path.join(root, file)
            
            if file_lower.endswith(".shp.shp") or file_lower.endswith(".tmp.shp"):
                continue

            if file_lower.endswith(".txt"):
                print("  [Sorting] Database text file -> {}".format(file))
                shutil.copy(src_file, os.path.join(data_dir, file))
            elif file_lower.endswith(".haz"):
                print("  [Sorting] Shading map -> {}".format(file))
                shutil.copy(src_file, os.path.join(shading_dir, file))
            elif file_lower.endswith(".dip") or file_lower.endswith(".ai"):
                print("  [Sorting] Game logic/AI module -> {}".format(file))
                shutil.copy(src_file, os.path.join(ai_logic_dir, file))

    print("\n[5/5] Purging temporary raw files...")
    try:
        shutil.rmtree(tmp_base)
        print("  -> Workspace cleaned. All temporary metadata cleared.")
    except Exception as e:
        print("  [Warning] Could not clear temp folder: {}".format(e))

    print("\n=== MASTER INGESTION COMPLETE ===")
    print("All files processed and structured inside: {}".format(target_path))


if __name__ == "__main__":
    main()
