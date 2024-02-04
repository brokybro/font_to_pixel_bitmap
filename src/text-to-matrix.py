# Create a bitmap/pixel representatmax_px_heightion of font in ttf in any font size

# Copyright (C) 2024 Jan Brokes

# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
# See LICENSE.GPL for license details.

from __future__ import print_function
from PIL import Image, ImageFont, ImageDraw
from typing import List, Tuple
import numpy as np
import math

# Path to ttf font
FONT_PATH = 'calibri.ttf'
# Path to output file
OUTPUT_FILE_PATH = 'output_file.cpp'
# All letters in the resulting bitmap
# Use unicode string for UTF characters 
ALL_LETTERS = u'0123456789.C° '

# String to write when pixel is on 
OUTPUT_FILL = '1'
# String to write when pixel is off
OUTPUT_EMPTY = '0'
# String to write on every line before output string
OUTPUT_SEPARATOR = '// '
# When true, write hexa bytes on every line before output string
OUTPUT_HEXA = True

'''
Choose font_size_option:
	'font_size' 	: Font size is defined beforehand 
	'letter_max_px_width'	: Font size is determined as maximum below px height limit of single letter
	'str_max_px_width'	: Font size is determined as maximum below px width limit of sample string
	'max_px_both'	: Font size is determined minimum of both px limits above
'''
FONT_SIZE_OPTION = 'max_px_both'

# Simply set font size to this value
FONT_SIZE = 60
# Program will determine maximum font size such that
# size in pixels adheres to both limits below 
# maximum height in pixels of any letter
LETTER_MAX_PX_WIDTH = 40
# Maximum width of the string below in pixels
STR_MAX_PX_WIDTH = 360
# Sample string to determine size by width
MAX_WIDTH_STRING = u'23.45°C'

# String to write to beginning of the file
def generate_header() -> str:
	header = '''
// This is a file generated by text-to-matrix.py
const uint8_t FontPy_Table [] = {
'''
	return header

# String to write at the end of the file
def generate_footer(max_width: int, actual_height: int) -> str:
	footer = f'''}};
  /* Width = {max_width} */
  /* Height = {actual_height} */
'''
	return footer

# -----------------------------------------------
# Below are private functions used in the script
# -----------------------------------------------

def get_letter_dimensions(text: str, font: ImageFont) -> Tuple[int, int]:
	'''
	Get dimensions of a single character in pixels
	'''
	l, t, r, b = font.getbbox(text)
	width = r - l
	height = b - t
	return width, height

def char_to_pixels(text: str, font: ImageFont, width: int, height: int) -> Tuple[np.ndarray, np.ndarray]:
	'''
	Convert character to binary array and create a mask
	'''
	image = Image.new('L', (width, height), 255)
	draw = ImageDraw.Draw(image)
	draw.text((0, 0), text, font=font)
	arr = np.asarray(image)
	arr = np.where(arr, 0, 255)
	arr_mask = (arr != 0).any(axis=1)
	return arr, arr_mask

def hex_with_padding(num: int, width: int) -> str:
	'''
	Convert integer to string of hex bytes with padding
	Example: '0x00, 0x00, 0x7f, 0xfe,'
	'''
	hex_str = format(num, f'0{width}x')
	pairs = ['0x' + hex_str[i:i + 2] for i in range(0, len(hex_str), 2)]
	return ', '.join(pairs)

def to_bitfield(file, arr: np.ndarray, max_height: int, max_width: int):
	'''
	Convert binary array to hex values and write to file
	'''
	new_array = np.zeros((max_height, max_width), dtype=arr.dtype)
	new_array[:arr.shape[0], :arr.shape[1]] = arr
	width = math.ceil(max_width / 4)
	binary_arr = np.where(new_array, 1, 0)
	hex_values = [hex_with_padding(int(''.join(map(str, row)), 2), width) for row in binary_arr]
	comment_arr = np.where(new_array, OUTPUT_FILL, OUTPUT_EMPTY)
	comments = [''.join(row) for row in comment_arr]
	if OUTPUT_HEXA:
		result = [f'{hexa},\t {OUTPUT_SEPARATOR}{com}' for hexa, com in zip(hex_values, comments)]
	else:
		result = [f'{OUTPUT_SEPARATOR}{com}' for com in comments]
	file.write('\n'.join(result))
	file.write('\n\n')

def determine_font_size_by_max_width(string: str, font: str, px_width : int) -> int:
	'''
	Determine maximum font size based on maximum pixel width
	'''
	max_width = 0
	size = 1
	last_size = size
	while max_width < px_width:
		font_inst = ImageFont.truetype(font=font, size=size)
		max_width, _ = get_letter_dimensions(string, font_inst)
		last_size = size
		size += 1
	if max_width > px_width:
		return last_size
	return size

def determine_font_size_by_max_height(string: str, font: str, px_height : int) -> int:
	'''
	Determine maximum font size based on maximum pixel height
	'''
	max_height = 0
	size = 1
	# Compensation for added rows at start and end for padding
	px_height -= 2
	last_size = size
	while max_height < px_height:
		font_inst = ImageFont.truetype(font=font, size=size)
		_, max_height = get_letter_dimensions(string, font_inst)
		last_size = size
		size += 1
	if max_height > px_height:
		return last_size
	return size

def get_max_letter_dimensions(base_string: str, font_inst: ImageFont) -> Tuple[int, int]:
	'''
	Get maximum pixel sizes for all letters in the string
	'''
	max_width, max_height = 0, 0
	for char in base_string:
		char_width, char_height = get_letter_dimensions(char, font_inst)
		max_width = max(char_width, max_width)
		max_height = max(char_height, max_height)
	max_height *= 2
	return max_width, max_height

def determine_final_height(masks: List[np.ndarray]) -> Tuple[List[bool], int]:
	'''
	Determine the final height and final mask based on the provided masks.
	'''
	total_mask = [False] * len(masks[-1])

	for mask in masks:
		for index, _ in enumerate(mask):
			if (mask[index] or mask[max(index - 1, 0)] or mask[min((index + 1), len(mask) - 1)]):
				total_mask[index] = True

	actual_height = total_mask.count(True)
	return total_mask, actual_height

def font_to_pixels(font_path: str, output_file_path: str, all_letters: str, 
				   font_size_option: str, letter_max_px_width: int, str_max_px_width: int, 
				   max_width_string: str, input_font_size: int):
	'''
	Convert font characters to pixel arrays and save to a file.
	'''
	font_size : int
	if font_size_option == 'font_size':
		font_size = input_font_size
	elif font_size_option == 'letter_max_px_width':
		font_size = determine_font_size_by_max_height(all_letters, font_path, letter_max_px_width)
	elif font_size_option == 'str_max_px_width':
		font_size = determine_font_size_by_max_width(max_width_string, font_path, str_max_px_width)
	elif font_size_option == 'max_px_both':
		size_by_height = determine_font_size_by_max_height(all_letters, font_path, letter_max_px_width)
		size_by_width = determine_font_size_by_max_width(max_width_string, font_path, str_max_px_width)
		font_size = min(size_by_height, size_by_width)

	font_inst = ImageFont.truetype(font=font_path, size=font_size)

	max_width, max_height = get_max_letter_dimensions(all_letters, font_inst)

	letters = []
	masks = []

	for char in all_letters:
		char_arr, char_mask = char_to_pixels(char, font_inst, max_width, max_height)
		letters.append(char_arr)
		masks.append(char_mask)

	total_mask, actual_height = determine_final_height(masks)

	print(f'Pixel size H x W: {actual_height} x {max_width}')

	with open(output_file_path, 'w') as file:
		file.write(generate_header())
		for char_arr in letters:
			char_arr = char_arr[total_mask]
			to_bitfield(file, char_arr, actual_height, max_width)
		file.write(generate_footer(max_width, actual_height))

def main():
	font_to_pixels(
		FONT_PATH,
		OUTPUT_FILE_PATH,
		ALL_LETTERS,
		FONT_SIZE_OPTION,
		LETTER_MAX_PX_WIDTH,
		STR_MAX_PX_WIDTH,
		MAX_WIDTH_STRING,
		FONT_SIZE
	)

if __name__ == '__main__':
	main()