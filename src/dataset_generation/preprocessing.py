#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Feb 15 2020

@author: thomaslamson
"""

import json
import os
import re
import matplotlib.pyplot as plt


# Constants
NOVEL_PATH = '../data/novel/'
NOVEL_SUFFIX = '_novel.json'
PREPROC_PATH = '../data/preproc/'
PREPROC_SUFFIX = '_preproc.json'
ENTSUM_PATH = '../data/ent_sum/'
ENTSUM_SUFFIX = '_entsum.json'


def separate_paragraphs_all_files(overwrite, min_threshold=20, min_length=600, max_length=900, verbose=1):
	files = os.listdir(NOVEL_PATH)
	treated_files = os.listdir(PREPROC_PATH)
	treated_ids = [f[:-len(PREPROC_SUFFIX)] for f in treated_files]

	for f in files:
		d_id = f[:-len(NOVEL_SUFFIX)]
		if not os.path.exists(NOVEL_PATH + d_id + NOVEL_SUFFIX):
			continue
		if overwrite or d_id not in treated_ids:
			separate_in_paragraphs(min_threshold, min_length, max_length, d_id, verbose)


def separate_in_paragraphs(min_threshold=20, min_length=600, max_length=900, d_id=None, verbose=2):
	target_length = (min_length + max_length) / 2

	# Input of file ID
	if d_id is None:
		while True:
			d_id = input("Select a novel id: ")
			if os.path.exists(NOVEL_PATH + d_id + NOVEL_SUFFIX):
				break
			print("ERROR - Id", d_id, "not found.")

	# Reading JSON file
	try:
		data = json.load(open(NOVEL_PATH + d_id + NOVEL_SUFFIX, 'r'))
	except UnicodeDecodeError:
		data = json.load(open(NOVEL_PATH + d_id + NOVEL_SUFFIX, 'r', encoding='utf-8'))
	novel_data = data['novel']
	full_text = novel_data['text']
	paragraphs = []

	if verbose >= 1:
		print("\n--- NOVEL DATA ---")
		print("Title:\t", novel_data['title'])
		print("Author:\t", novel_data['author'])
		print("Theme:\t", novel_data['theme'])
		print("Text:\t\"", full_text[:100].replace('\n', ' ') + "...\"")

	# Parsing paragraphs
	def add_paragraph(content):
		c = content.strip()
		assert len(c) <= max_length
		paragraphs.append({
			'size': len(c),
			'text': c
		})

	# Removing any isolated line-breaks, any multiple whitespaces and separating in real paragraphs
	striped_of_linebreaks = ' '.join('\n' if elt == '' else elt for elt in full_text.split('\n'))
	striped_of_multispaces = re.sub(r'[ ]+', ' ', striped_of_linebreaks)
	real_paragraphs = [elt.strip() for elt in striped_of_multispaces.split('\n') if elt != '']

	parts = []
	current_part = []
	for i, p in enumerate(real_paragraphs):
		if len(p) <= min_threshold:
			if len(current_part) > 0:
				parts.append(current_part)
				current_part = []
			continue
		current_part.append(p)
	if len(current_part) > 0:
		parts.append(current_part)

	# Computing statistics on book
	content_length = 0
	if verbose >= 1:
		avg_paragraphs_per_part = sum(len(part) for part in parts) / len(parts)
		content_length = sum(sum(len(paragraph) for paragraph in part) for part in parts)
		num_paragraphs = sum(len(part) for part in parts)
		avg_paragraph_length = content_length / num_paragraphs
		print("\n--- NOVEL STATISTICS ---")
		print("Content length:\t\t\t\t", content_length)
		print("Parts:\t\t\t\t\t\t", len(parts))
		print("Paragraphs:\t\t\t\t\t", num_paragraphs)
		print("Paragraphs per part:\t\t {:.2f}".format(avg_paragraphs_per_part))
		print("Average paragraph length:\t {:.2f}".format(avg_paragraph_length))

	# Propagating small parts (< MIN_LENGTH) to next parts, because it probably comes from wrong parsing
	i = 0
	while i < len(parts):
		if sum(len(p) for p in parts[i]) >= min_length:
			i += 1
		elif i < len(parts) - 1:
			part = parts.pop(i)
			parts[i] = part + parts[i]
		else:
			break

	# Beginning the splitting of paragraphs
	for part_i, part in enumerate(parts):
		for pi, rp in enumerate(part):
			if rp == "":
				continue

			# Lookahead: to prevent small trail paragraphs, we look ahead and add to current paragraph
			# the next ones as long as they are less than the minimum length.
			while pi + 1 < len(part) and len(part[pi + 1]) < min_length:
				np = part.pop(pi + 1)
				rp = rp + ' ' + np

			# Paragraph is of correct size, or is too short but is the last one of current part --> Add it as is.
			if min_length <= len(rp) <= max_length or (len(rp) < min_length and pi == len(part) - 1):
				add_paragraph(rp)

			# Paragraph is too short --> Add it to the beginning of the next one.
			elif len(rp) < min_length:
				part[pi + 1] = rp + part[pi + 1]

			# Paragraph is too long --> Split it in parts and add the remaining to the next one.
			else:
				# Splitting the paragraph at target_length, without cutting words
				#  1. We add words until we pass MIN_LENGTH
				#  2. If we encounter a final point, we end the split. --> NEXT (with empty)
				#  3. When we pass TARGET_LENGTH, we keep a memory of the current paragraph.
				#  4. If we encounter a final point, we end the split. --> NEXT (with empty)
				#  5. When we pass MAX_LENGTH, we end the split with step 3's memory. --> NEXT (with current - saved)
				#  6. If end of paragraph and we are below MIN_LENGTH, add to next paragraph. --> END
				to_add = []
				current_split = ""
				saved_split = ""
				words = rp.split(' ')
				for wi, w in enumerate(words):
					current_split = (current_split + " " + w).strip()
					final_point = current_split[-1] in ['.', '!', '?', '\'', '"']
					if min_length <= len(current_split) <= max_length and final_point:
						to_add.append(current_split)
						current_split = ""
						saved_split = ""
					elif max_length <= len(current_split):
						to_add.append(saved_split.strip())
						current_split = current_split[len(saved_split):].strip()
						saved_split = ""
					elif target_length <= len(current_split) and saved_split == "":
						saved_split = current_split
					elif wi == len(words) - 1:  # current_split is too small, and it's the end of the paragraph
						if pi < len(part) - 1:  # there is still a paragraph after that
							part[pi + 1] = current_split + ' ' + part[pi + 1]
						else:					# there is no paragraph in this part
							# We check if we can put it back to the previous paragraph
							if len(to_add) > 0 and len(to_add[-1]) + len(current_split) + 1 <= max_length:
								to_add[-1] += ' ' + current_split
							else:
								# Else we add it as is
								to_add.append(current_split.strip())
								if len(current_split) < 60:
									print("Adding too small, L:", len(current_split))
									print(current_split)
									print(to_add[-2])
				for p in to_add:
					add_paragraph(p)

	# Saving JSON file
	novel_data.pop('text')
	novel_data['paragraphs'] = paragraphs
	json.dump(data, open(PREPROC_PATH + d_id + PREPROC_SUFFIX, 'w'))

	# Printing results
	if verbose >= 1:
		sizes = []
		for p in paragraphs:
			sizes.append(p['size'])

		print("\n--- EXTRACTED GROUPS ---")
		print('Groups:\t\t\t\t', len(sizes))
		print('Average length:\t\t', int(sum(sizes) / len(sizes)))
		print('Max length:\t\t\t', max(sizes))
		print('Min length:\t\t\t', min(sizes))
		print('% of raw text:\t\t {}%'.format(int(100 * sum(sizes) / len(full_text))))
		print('% of clean text:\t {}%'.format(int(100 * sum(sizes) / content_length)))
		print('\n-- First paragraph:\n"' + paragraphs[0]['text'][:100] + '..."')

		if verbose >= 2:
			plt.hist(sizes)
			plt.show()

