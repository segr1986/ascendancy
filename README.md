# ascendancy #

Utilities to extract and convert Ascendancy game resources (fully modernized for Python 3). 

*Refactored, debugged, and optimized in 2026 by an adaptive AI collaborator to guarantee bit-perfect RLE coordinate bounds rendering, structural pipeline stability, and asset extraction verification.*

## commands ##

- **extract_all.py** /path/to/cd_drive /path/to/output_assets
- **cob.py** file.cob [output_directory]
- **font.py** file.fnt file.pal
- **shape.py** file.shp file.pal
- **voice.py** file.voc
- **music.py** file.raw

## ingestion automation ##

To automatically unpack the full game CD, align regional color palettes, and neatly structure all game assets, place all script files in the same directory and execute:

    python3 extract_all.py /media/cdrom ~/dev/ascendancy_godot/assets

## resource guide ##

If you choose to run the extraction manually, parse the files as follows:

    mkdir cob0 cob1 cob2
    python3 cob.py ASCEND00.COB cob0
    python3 cob.py ASCEND01.COB cob1
    python3 cob.py ASCEND02.COB cob2

    cob0/*.txt - Plain text databases (e.g., gizmos.txt for ship components)
         *.dip - Binary diplomacy logic charts
         *.ai  - Binary AI behavior scripts

    cob1/data/*.dll - Legacy engine data
              *.fnt - Font graphics => python3 font.py font.fnt subfont.pal
              *.gif - Standard GIF graphics
              *.haz - 256-Byte color-remapping lookup tables for shading and transparency
              *.pal - VGA color palettes (game.pal for standard sprites, subfont.pal for text)
              *.shp - Shape/Sprite files => python3 shape.py graphic.shp game.pal
              *.tmp - Interface shape files (identical to SHP architecture; natively unpackable via shape.py)
              *.voc - Interface and sound effect files => python3 voice.py effect.voc

    cob2/*.tsv - Tutorial animation scripts and timestamp metadata text files
         *.bin - Autodesk Animator (FLI/FLC) container files for background cutscenes
         data/*.flc - Standard Autodesk FLC animation reels
              *.fnt - Contextual introductory fonts => python3 font.py intro.fnt intro.pal
              *.gif - Standard GIF graphics
              *.raw - Uncompressed raw 8-Bit Mono 22050Hz PCM music streams => python3 music.py track.raw

