import os
import struct
import glob
from PIL import Image

def parse_rpt_header(data):
    """
    Parses the 0x40 byte header.
    Returns (width, height) if valid RPT header, otherwise (None, None).
    """
    if len(data) < 0x40:
        return None, None
        
    # Check Magic Bytes at offset 0: \x00RPT
    magic = data[0:4]
    if magic != b'\x00RPT':
        return None, None

    # Width at 0x20, Height at 0x24 (Big-Endian 32-bit integers)
    width = struct.unpack('>I', data[0x20:0x24])[0]
    height = struct.unpack('>I', data[0x24:0x28])[0]
    
    return width, height

def convert_rpt_to_png(filepath, force_format=None, output_dir = None):
    """
    Converts a single .rpt file to a .png image.
    Attempts to guess format from filename if force_format isn't provided.
    """
    with open(filepath, 'rb') as f:
        file_data = f.read()

    width, height = parse_rpt_header(file_data)
    if width is None or height is None:
        print(f"[-] Skipped: {filepath} (Not a valid RPT file or missing magic bytes)")
        return

    # Raw pixel data starts after the 0x40 header
    pixel_data = file_data[0x40:]
    total_pixels = width * height

    # Determine N64 texture format archetype from filename hints
    filename_lower = filepath.lower()
    fmt = force_format
    if not fmt:
        if 'rgba16' in filename_lower: fmt = 'rgba16'
        elif 'rgba32' in filename_lower: fmt = 'rgba32'
        elif 'ia4' in filename_lower:  fmt = 'ia4'
        elif 'ia8' in filename_lower:  fmt = 'ia8'
        elif 'ia16' in filename_lower: fmt = 'ia16'
        elif 'i4' in filename_lower:   fmt = 'i4'
        elif 'i8' in filename_lower:   fmt = 'i8'
        else:
            fmt = 'rgba32' # Default fallback if no tag matches

    print(f"[*] Processing {os.path.basename(filepath)}: {width}x{height} [{fmt.upper()}]")

    # Create target buffer for standard 32-bit RGBA image
    rgba_output = bytearray(total_pixels * 4)

    for p in range(total_pixels):
        out_idx = p * 4
        r, g, b, a = 0, 0, 0, 255

        if fmt == 'rgba32':
            b_idx = p * 4
            if b_idx + 3 < len(pixel_data):
                r, g, b, a = pixel_data[b_idx:b_idx+4]

        elif fmt == 'rgba16':
            b_idx = p * 2
            if b_idx + 1 < len(pixel_data):
                val = struct.unpack('>H', pixel_data[b_idx:b_idx+2])[0]
                r = int(((val >> 11) & 0x1F) * 255 / 31)
                g = int(((val >> 6) & 0x1F) * 255 / 31)
                b = int(((val >> 1) & 0x1F) * 255 / 31)
                a = 255 if (val & 0x01) else 0

        elif fmt == 'i4':
            byte_pos = p // 2
            if byte_pos < len(pixel_data):
                raw_byte = pixel_data[byte_pos]
                i4_val = (raw_byte >> 4) if (p % 2 == 0) else (raw_byte & 0x0F)
                r = g = b = int(i4_val * 255 / 15)

        elif fmt == 'i8':
            if p < len(pixel_data):
                r = g = b = pixel_data[p]

        elif fmt == 'ia4':
            byte_pos = p // 2
            if byte_pos < len(pixel_data):
                raw_byte = pixel_data[byte_pos]
                bits = (raw_byte >> 4) if (p % 2 == 0) else (raw_byte & 0x0F)
                r = g = b = int(((bits >> 1) & 0x07) * 255 / 7)
                a = 255 if (bits & 0x01) else 0

        elif fmt == 'ia8':
            if p < len(pixel_data):
                raw_byte = pixel_data[p]
                r = g = b = int(((raw_byte >> 4) & 0x0F) * 255 / 15)
                a = int((raw_byte & 0x0F) * 255 / 15)

        elif fmt == 'ia16':
            b_idx = p * 2
            if b_idx + 1 < len(pixel_data):
                r = g = b = pixel_data[b_idx]
                a = pixel_data[b_idx + 1]

        rgba_output[out_idx:out_idx+4] = [r, g, b, a]

    # Use Pillow to build image object and output
    img = Image.frombytes("RGBA", (width, height), bytes(rgba_output))
    # Split the original path into directory and filename components
    dir_name = os.path.dirname(filepath)
    file_name = os.path.basename(filepath)
    base_name = os.path.splitext(file_name)[0]

    # Create the path to the 'bin' folder inside the target directory
    bin_dir = os.path.join(dir_name, "bin")
    os.makedirs(bin_dir, exist_ok=True)  # Creates the 'bin' directory if it doesn't exist

    # Combine them into the final output path
    if output_dir is not None:
        bin_dir = output_dir
    output_path = os.path.join(bin_dir, base_name + ".png")
    img.save(output_path)
    print(f"[+] Saved: {output_path}")