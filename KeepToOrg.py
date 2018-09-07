import os
import html
import sys

"""
KeepToOrg.py

Usage:
    python KeepToOrg.py /path/to/google/Keep

Given a Takeout of your Google Keep Notes in .html format, output .org files with logical groupings 
based on tags. This will also format lists and try to be smart.
"""

# TODO: Format links:
# Links have the syntax [[https://blah][Example link]] (things can be internal links too!)
# See https://orgmode.org/manual/External-links.html

# Convert an array of tags to an Emacs Org tag string
# Tags have the syntax :tag: or :tag1:tag2:
def tagsToOrgString(tags):
    if len(tags) == 0:
        return ''

    tagString = ':'
    for tag in tags:
        tagString += tag + ':'

    return tagString

class Note:
    def __init__(self):
        self.title = ""
        self.body = ""
        self.tags = []
        self.archived = False

    def toOrgString(self):
        status = '(ARCHIVED) ' if self.archived else ''

        # Convert lists to org lists. This is a total hack but works
        self.body = self.body.replace('<li class="listitem"><span class="bullet">&#9744;</span>\n', '- [ ] ')
        self.body = self.body.replace('<li class="listitem checked"><span class="bullet">&#9745;</span>', '- [X] ')
        # Flat out remove these
        for htmlTagToErase in ['<span class="text">', '</span>', '</li>', '<ul class="list">', '</ul>']:
            self.body = self.body.replace(htmlTagToErase, '')
        # This is very weird, but fix the edge case where the list entry has a new line before the content
        for listTypeToFixNewLines in ['- [ ] \n','- [X] \n']:
            self.body = self.body.replace(listTypeToFixNewLines, listTypeToFixNewLines[:-1])

        # Unescape all (e.g. remove &quot and replace with ")
        self.title = html.unescape(self.title)
        self.body = html.unescape(self.body)
        for i, tag in enumerate(self.tags):
            self.tags[i] = html.unescape(tag)

        # Strip tags
        for tag in self.tags:
            self.body = self.body.replace('#{}'.format(tag), '')

        # Remove any leading/trailing whitespace (possibly leftover from tags stripping)
        self.body = self.body.strip()

        # Make a title if necessary
        orgTitle = self.title
        if not orgTitle:
            toNewline = self.body.find('\n')
            if toNewline >= 0:
                orgTitle = self.body[:toNewline]
                self.body = self.body[len(orgTitle) + 1:]
            else:
                orgTitle = self.body
                # If the title is the whole body, clear the body
                self.body = ''

        if self.body or len(self.tags):
            if self.body and not len(self.tags):
                return '* {}{}\n{}'.format(status, orgTitle, self.body)
            if not self.body and len(self.tags):
                return '* {}{}\n{}'.format(status, orgTitle, tagsToOrgString(self.tags))
            else:
                return "* {}{}\n{}\n{}".format(status, orgTitle, self.body, tagsToOrgString(self.tags))
        # If no body nor tags, note should be a single line
        else:
            return "* {}{}".format(status, orgTitle)

def getAllNoteHtmlFiles(htmlDir):
    print('Looking for notes in {}'.format(htmlDir))
    noteHtmlFiles = []
    for root, dirs, files in os.walk(htmlDir):
        for file in files:
            if file.endswith(".html"):
                noteHtmlFiles.append(os.path.join(root, file))

    print ('Found {} notes'.format(len(noteHtmlFiles)))
    return noteHtmlFiles

def getHtmlValueIfMatches(line, tag, endTag):
    if tag.lower() in line.lower() and endTag.lower() in line.lower():
        return line[line.find(tag) + len(tag):-(len(endTag) + 1)], True
    return '', False

def main(keepHtmlDir):
    noteFiles = getAllNoteHtmlFiles(keepHtmlDir)
    
    for noteFilePath in noteFiles:
        # Read in the file
        noteFile = open(noteFilePath)
        noteLines = noteFile.readlines()
        noteFile.close()

        print('\nParsing {}'.format(noteFilePath))

        note = Note()
        
        readState = 'lookingForAny'
        numOpenedDivs = 0
        for line in noteLines:
            isMatch = False

            numOpenedDivs += line.count('<div')
            numOpenedDivs -= line.count('</div>')

            if readState == 'lookingForAny':
                if '<span class="archived" title="Note archived">' in line:
                    note.archived = True
                    
                # Parse date (for sorting)
                # Parse title
                title, isMatch = getHtmlValueIfMatches(line, '<div class="title">', '</div>')
                if isMatch:
                    note.title = title
                    continue
                
                if '<div class="content">' in line:
                    readState = 'parsingBody'

                    # This isn't great; for same-line bodies, strip opening div
                    line = line.replace('<div class="content">', '')

                # Parse tags
                potentialTag, isMatch = getHtmlValueIfMatches(line, '<span class="label-name">', '</span>')
                if isMatch:
                    note.tags.append(potentialTag)
                    continue

            # Parse body
            if readState == 'parsingBody':
                if line.strip().lower() == '<br>':
                    line = '\n'
                    
                if line.strip().lower().endswith('</div>') and numOpenedDivs == 1:
                    line = line[:-(len('</div>') + 1)]
                    readState = 'lookingForAny'

                note.body += line.replace('<br>', '\n')

        print(note.toOrgString())

        # TODO: Add to org list depending on tags

if __name__ == '__main__':
    if len(sys.argv) != 2:
        print('Wrong number of arguments!\nUsage:\n\tpython KeepToOrg.py /path/to/google/Keep')

    else:
        keepHtmlDir = sys.argv[1]
        main(keepHtmlDir)

