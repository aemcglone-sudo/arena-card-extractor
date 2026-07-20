#!/usr/bin/env python3
"""
Magic Card Name Extractor
Extracts card names from Magic: The Gathering card images using OCR.
"""

import pytesseract
from PIL import Image
import sys
import os
import re
import csv
import base64
import argparse
from pathlib import Path
from datetime import datetime

CLAUDE_MODEL = "claude-haiku-4-5"

def clean_card_name(line):
    """Strip mana-symbol OCR noise and stray punctuation from a name line."""
    line = re.sub(r'\{.*?\}', '', line)
    # Trim leading/trailing characters that aren't letters, digits, apostrophes, commas, or hyphens
    line = re.sub(r"^[^A-Za-z0-9']+|[^A-Za-z0-9]+$", '', line)
    return line.strip()

def extract_card_names_from_image(image_path):
    """
    Extract card names from a single image.
    Returns a tuple: (card_name, extracted_text)
    """
    try:
        img = Image.open(image_path)

        if img.mode != 'RGB':
            img = img.convert('RGB')

        # The card name only ever appears in the title bar at the top of the
        # card, so cropping there avoids picking up type lines and rules text.
        width, height = img.size
        title_crop = img.crop((0, 0, width, int(height * 0.12)))

        text = pytesseract.image_to_string(title_crop)
        lines = [clean_card_name(l) for l in text.strip().split('\n')]

        for line in lines:
            if line and len(line) > 2:
                return line, text

        return None, text

    except Exception as e:
        print(f"Error processing {image_path}: {e}")
        return None, None

def extract_card_names_claude(image_path, client):
    """
    Extract Magic card name(s) from an image using Claude Vision (Haiku).
    Handles images containing one or several cards.
    Returns a list of card names (possibly empty).
    """
    media_types = {
        '.png': 'image/png', '.jpg': 'image/jpeg', '.jpeg': 'image/jpeg',
        '.gif': 'image/gif', '.webp': 'image/webp',
    }
    media_type = media_types.get(Path(image_path).suffix.lower(), 'image/png')

    with open(image_path, 'rb') as f:
        image_data = base64.b64encode(f.read()).decode()

    try:
        response = client.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=500,
            messages=[{
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {"type": "base64", "media_type": media_type, "data": image_data},
                    },
                    {
                        "type": "text",
                        "text": "This image shows one or more Magic: The Gathering cards. "
                                "List the name of every card you can identify, one per line, "
                                "with no numbering, bullets, or other text. "
                                "If you cannot identify any cards, reply with exactly: NONE",
                    },
                ],
            }],
        )
        text = response.content[0].text.strip()
        if text == "NONE":
            return []
        return [line.strip() for line in text.split('\n') if line.strip()]
    except Exception as e:
        print(f"Error processing {image_path}: {e}")
        return []

def write_txt(output_path, card_data):
    """Write card names to TXT file as '1 Card Name' per line."""
    with open(output_path, 'w') as f:
        for card_name, _ in card_data:
            if card_name:
                f.write(f'1 {card_name}\n')

def write_csv(output_path, card_data):
    """Write card data to CSV file."""
    with open(output_path, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['Card Name', 'Image Source', 'Extracted Date'])
        for card_name, image_source in card_data:
            if card_name:
                writer.writerow([card_name, image_source, datetime.now().isoformat()])

def process_folder(folder_path, output_file, format_type, client=None):
    """
    Process all images in a folder and extract card names.
    """
    folder = Path(folder_path)
    image_extensions = {'.png', '.jpg', '.jpeg', '.gif', '.bmp', '.webp'}

    card_data = []
    processed = 0

    for image_file in sorted(folder.iterdir()):
        if image_file.suffix.lower() in image_extensions:
            print(f"Processing: {image_file.name}")
            if client:
                names = extract_card_names_claude(str(image_file), client)
            else:
                card_name, _ = extract_card_names_from_image(str(image_file))
                names = [card_name] if card_name else []
            for name in names:
                card_data.append((name, image_file.name))
            processed += 1

    output_path = Path(output_file)
    if format_type == 'csv':
        write_csv(output_path, card_data)
    else:
        write_txt(output_path, card_data)

    print(f"\nProcessed {processed} images")
    print(f"Found {len(card_data)} card names")
    print(f"Format: {format_type.upper()}")
    print(f"Saved to: {output_path.absolute()}")

def process_single_image(image_path, output_file, format_type, client=None):
    """
    Process a single image and extract card names.
    """
    print(f"Processing: {image_path}")
    if client:
        names = extract_card_names_claude(image_path, client)
    else:
        card_name, _ = extract_card_names_from_image(image_path)
        names = [card_name] if card_name else []

    output_path = Path(output_file)

    if names:
        if format_type == 'csv':
            file_exists = output_path.exists()
            with open(output_path, 'a' if file_exists else 'w', newline='') as f:
                writer = csv.writer(f)
                if not file_exists:
                    writer.writerow(['Card Name', 'Image Source', 'Extracted Date'])
                for name in names:
                    writer.writerow([name, Path(image_path).name, datetime.now().isoformat()])
        else:
            mode = 'a' if output_path.exists() else 'w'
            with open(output_path, mode) as f:
                for name in names:
                    f.write(f'1 {name}\n')

        print(f"Found: {', '.join(names)}")
    else:
        print("No card name found")

    print(f"Saved to: {output_path.absolute()}")

if __name__ == '__main__':
    DEFAULT_FOLDER = os.path.expanduser('~/Desktop/Card Photos')
    DEFAULT_OUTPUT_DIR = os.path.expanduser('~/Desktop/MTGA')

    parser = argparse.ArgumentParser(description='Extract Magic card names from images')
    parser.add_argument('path', nargs='?', default=DEFAULT_FOLDER,
                        help=f'Path to image file or folder (default: {DEFAULT_FOLDER})')
    parser.add_argument('--format', choices=['txt', 'csv'], default='txt',
                        help='Output format (default: txt)')
    parser.add_argument('--output', default=None,
                        help='Output filename (default: card_names_<timestamp>.txt/.csv)')
    parser.add_argument('--claude-vision', action='store_true',
                        help='Use Claude Vision (Haiku) instead of local OCR for better accuracy. '
                             'Requires ANTHROPIC_API_KEY to be set.')

    args = parser.parse_args()

    if args.output:
        output_file = args.output
    else:
        timestamp = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
        output_file = os.path.join(DEFAULT_OUTPUT_DIR, f'card_names_{timestamp}.{args.format}')

    client = None
    if args.claude_vision:
        import anthropic
        client = anthropic.Anthropic()

    if os.path.isdir(args.path):
        process_folder(args.path, output_file, args.format, client)
    elif os.path.isfile(args.path):
        process_single_image(args.path, output_file, args.format, client)
    else:
        print(f"Error: Path not found: {args.path}")
        sys.exit(1)
