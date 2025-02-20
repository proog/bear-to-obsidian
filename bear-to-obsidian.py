import os
import re
import sys
from os.path import basename, dirname, isdir, isfile, join

ATTACHMENTS_DIR = "_attachments"


def main():
    if (len(sys.argv) < 2):
        print("Usage: python3 bear-to-obsidian.py /path/to/exported-bear-notes/")
        sys.exit(1)

    path = sys.argv[1]
    note_count = 0

    for filename in os.listdir(path):
        filename = join(path, filename)

        print("Processing %s" % filename)

        if isfile(filename) and filename.endswith(".md"):
            perform_edits(filename)
            move_note(filename)
            note_count += 1
        elif (
            isdir(filename)
            and basename(filename) != ATTACHMENTS_DIR
            and not basename(filename).startswith(".")
        ):
            move_attachments_dir(filename)

    print("Processed %i notes" % note_count)


def perform_edits(filename):
    stat = os.stat(filename)

    with open(filename, "r") as f:
        contents = f.read()

    contents = remove_toplevel_heading(contents)
    contents = increase_indentation(contents)
    contents = convert_embeds(contents)
    contents = replace_heading_links(contents)

    with open(filename, "w") as f:
        f.write(contents)

    # Restore original modification timestamp
    os.utime(filename, (stat.st_atime, stat.st_mtime))


def remove_toplevel_heading(note_contents):
    """Obsidian already shows the filename in a way visually similar to a top-level heading"""
    return re.sub(r"^# .+?\n\n?", "", note_contents)


def increase_indentation(note_contents):
    """Bear exports use 2-space list indents, but Obsidian renders them best with 4"""
    return re.sub(
        r"^(\ {2,})(-|\*|\d+\.) ", r"\1\1\2 ", note_contents, flags=re.MULTILINE
    )


def convert_embeds(note_contents):
    """Replace embed comments such as <!-- {"preview":"true"} --> comments with ![]"""
    note_contents = re.sub(
        r"^(\[.+\]\((?!https?://).+\))<!-- {.*\"preview\":\"true\".*} -->",
        r"!\1",
        note_contents,
        flags=re.MULTILINE,
    )
    note_contents = re.sub(
        r"^(\[.+\]\(.+\))<!-- {.*\"(preview|embed)\":\"true\".*} -->",
        r"\1",
        note_contents,
        flags=re.MULTILINE,
    )
    return note_contents


def replace_heading_links(note_contents):
    """Bear uses [[Wikilink/Heading]] syntax while Obsidian uses [[Wikilink#Heading]]"""
    return re.sub(r"\[\[(.+)?/(.+)\]\]", r"[[\1#\2]]", note_contents)


def move_attachments_dir(filename):
    """
    Bear exports attachments to a folder next to each note.
    This moves that folder into the global attachments folder.
    """
    attachments_dir = join(dirname(filename), ATTACHMENTS_DIR, basename(filename))
    os.renames(filename, attachments_dir)


def move_note(filename):
    """Moves the note into a folder structure named after its first tag, unless multiple tags are found"""
    tags = get_tags(filename)

    if len(tags) == 0:
        print("Found no tags for %s, won't move it" % filename)
        return

    if len(tags) > 1:
        print("Found multiple tags for %s, won't move it" % filename)
        return

    dirs = beautify_tag(tags[0]).split("/")
    new_filename = join(dirname(filename), *dirs, basename(filename))
    os.renames(filename, new_filename)


def get_tags(filename: str) -> list[str]:
    """
    Gets a list of tags from a note, excluding # symbol.
    Supports nested tags, but not multi-word tags.
    """
    with open(filename) as f:
        contents = f.read()
        return re.findall(r"(?:^|\s)#([\w,.-]+(?:/[\w,.-]+)?)", contents)


def beautify_tag(tag: str) -> str:
    """Capitalize and humanize each part of a (potentially nested) tag"""
    tag_words = [tag_word.replace("-", " ").capitalize() for tag_word in tag.split("/")]
    return "/".join(tag_words)


if __name__ == "__main__":
    main()
