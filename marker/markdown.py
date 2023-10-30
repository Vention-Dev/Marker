from marker.schema import MergedLine, MergedBlock, FullyMergedBlock, Page
import re
from typing import List


def surround_text(s, char_to_insert):
    leading_whitespace = re.match(r'^(\s*)', s).group(1)
    trailing_whitespace = re.search(r'(\s*)$', s).group(1)
    stripped_string = s.strip()
    modified_string = char_to_insert + stripped_string + char_to_insert
    final_string = leading_whitespace + modified_string + trailing_whitespace
    return final_string


def merge_spans(blocks):
    merged_blocks = []
    for page in blocks:
        page_blocks = []
        for blocknum, block in enumerate(page.blocks):
            block_lines = []
            block_types = []
            for linenum, line in enumerate(block.lines):
                line_text = ""
                if len(line.spans) == 0:
                    continue
                fonts = []
                for i, span in enumerate(line.spans):
                    font = span.font.lower()
                    next_font = None
                    if len(line.spans) > i + 1:
                        next_font = line.spans[i + 1].font.lower()
                    fonts.append(font)
                    block_types.append(span.block_type)
                    span_text = span.text
                    if "ital" in font and (not next_font or "ital" not in next_font):
                        span_text = surround_text(span_text, "*")
                    elif "bold" in font and (not next_font or "bold" not in next_font):
                        span_text = surround_text(span_text, "**")
                    line_text += span_text
                block_lines.append(MergedLine(
                    text=line_text,
                    fonts=fonts,
                    bbox=line.bbox
                ))
            if len(block_lines) > 0:
                page_blocks.append(MergedBlock(
                    lines=block_lines,
                    pnum=block.pnum,
                    bbox=block.bbox,
                    block_types=block_types
                ))
        merged_blocks.append(page_blocks)

    return merged_blocks


def block_surround(text, block_type):
    dot_pattern = re.compile(r'(\s*\.\s*){4,}')
    dot_multiline_pattern = re.compile(r'.*(\s*\.\s*){4,}.*', re.DOTALL)
    match block_type:
        case "Section-header":
            if not text.startswith("#"):
                text = "\n## " + text.strip() + "\n"
        case "Title":
            if not text.startswith("#"):
                text = "# " + text.strip() + "\n"
        case "Table" if dot_multiline_pattern.match(text):
            text = dot_pattern.sub(' ', text)
        case "List-item":
            pass
        case "Code":
            text = "```\n" + text + "\n```\n"
        case _:
            pass
    return text


def line_separator(line1, line2, block_type, is_continuation=False):
    # Remove hyphen in current line if next line and current line appear to be joined
    hyphen_pattern = re.compile(r'.*[a-z][-]\s?$', re.DOTALL)
    if line1 and hyphen_pattern.match(line1) and re.match(r"^[a-z]", line2):
        # Split on — or - from the right
        line1 = re.split(r"[-—]\s?$", line1)[0]
        return line1.rstrip() + line2.lstrip()

    lowercase_pattern1 = re.compile(r'.*[a-z,]\s?$', re.DOTALL)
    lowercase_pattern2 = re.compile(r'^\s?[A-Za-z]', re.DOTALL)
    end_pattern = re.compile(r'.*[.?!]\s?$', re.DOTALL)

    if block_type in ["Title", "Section-header"]:
        return line1.rstrip() + " " + line2.lstrip()
    elif lowercase_pattern1.match(line1) and lowercase_pattern2.match(line2):
        return line1.rstrip() + " " + line2.lstrip()
    elif is_continuation:
        return line1.rstrip() + " " + line2.lstrip()
    elif block_type == "Text" and end_pattern.match(line1):
        return line1 + "\n\n" + line2
    elif block_type == "Formula":
        return line1 + " " + line2
    else:
        return line1 + "\n" + line2


def block_separator(line1, line2, block_type1, block_type2):
    sep = "\n"
    if block_type1 == "Text":
        sep = "\n\n"

    return sep + line2


def merge_lines(blocks, page_blocks: List[Page]):
    text_blocks = []
    prev_type = None
    prev_line = None
    block_text = ""
    block_type = ""
    common_line_heights = [p.get_line_height_stats() for p in page_blocks]
    for page in blocks:
        for block in page:
            block_type = block.most_common_block_type()
            if block_type != prev_type and prev_type:
                text_blocks.append(
                    FullyMergedBlock(
                        text=block_surround(block_text, prev_type),
                        block_type=prev_type
                    )
                )
                block_text = ""

            prev_type = block_type
            common_line_height = common_line_heights[block.pnum].most_common(1)[0][0]
            for i, line in enumerate(block.lines):
                line_height = line.bbox[3] - line.bbox[1]
                prev_line_height = prev_line.bbox[3] - prev_line.bbox[1] if prev_line else 0
                prev_line_x = prev_line.bbox[0] if prev_line else 0
                prev_line = line
                is_continuation = line_height == prev_line_height and line.bbox[0] == prev_line_x
                if block_text:
                    block_text = line_separator(block_text, line.text, block_type, is_continuation)
                else:
                    block_text = line.text

    # Append the final block
    text_blocks.append(
        FullyMergedBlock(
            text=block_surround(block_text, prev_type),
            block_type=block_type
        )
    )
    return text_blocks


def get_full_text(text_blocks):
    full_text = ""
    prev_block = None
    for block in text_blocks:
        if prev_block:
            full_text += block_separator(prev_block.text, block.text, prev_block.block_type, block.block_type)
        else:
            full_text += block.text
        prev_block = block
    return full_text
