import os
import html
import sys
import datetime

"""
KeepToOrg.py

Usage:
    python KeepToOrg.py /path/to/google/Keep output/dir

Given a Takeout of your Google Keep Notes in .html format, output .org files with logical groupings 
based on tags. This will also format lists and try to be smart.
"""

# TODO:
# Format links:
#   Links have the syntax [[https://blah][Example link]] (things can be internal links too!)
#   See https://orgmode.org/manual/External-links.html

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
        self.title = ''
        self.body = ''
        self.tags = []
        self.archived = False
        # If no date can be parsed, set it to Jan 1, 2000
        self.date = datetime.datetime(2000, 1, 1)

    def toOrgString(self):
        # status = '(archived) ' if self.archived else ''
        # Create a copy so we can mangle it
        body = self.body
        title = self.title

        # Convert lists to org lists. This is a total hack but works
        body = body.replace('<li class="listitem"><span class="bullet">&#9744;</span>\n', '- [ ] ')
        body = body.replace('<li class="listitem checked"><span class="bullet">&#9745;</span>', '- [X] ')
        # Flat out remove these
        for htmlTagToErase in ['<span class="text">', '</span>', '</li>', '<ul class="list">', '</ul>']:
            body = body.replace(htmlTagToErase, '')
        # This is very weird, but fix the edge case where the list entry has a new line before the content
        for listTypeToFixNewLines in ['- [ ] \n','- [X] \n']:
            body = body.replace(listTypeToFixNewLines, listTypeToFixNewLines[:-1])

        # Unescape all (e.g. remove &quot and replace with ")
        title = html.unescape(title)
        body = html.unescape(body)
        for i, tag in enumerate(self.tags):
            self.tags[i] = html.unescape(tag)

        # Strip tags
        for tag in self.tags:
            body = body.replace('#{}'.format(tag), '')

        # Remove any leading/trailing whitespace (possibly leftover from tags stripping)
        body = body.strip()

        # Make a title if necessary
        orgTitle = title
        if not orgTitle:
            toNewline = body.find('\n')
            # If there's a line break; use the first line as a title
            if toNewline >= 0:
                orgTitle = body[:toNewline]
                body = body[len(orgTitle) + 1:]
            # The note has no breaks; make the body the title
            else:
                orgTitle = body
                # If the title is the whole body, clear the body
                body = ''

        nesting = '*' if self.archived else ''
        # Various levels of information require different formats
        created = self.date.strftime(":PROPERTIES:\n:CREATED:  [%Y-%m-%d %a %H:%M]\n:END:")
        if body or len(self.tags):
            if body and not len(self.tags):
                return '*{} {}\n{}\n{}'.format(nesting, orgTitle, created, body)
            if not body and len(self.tags):
                return '*{} {} {}\n{}\n'.format(nesting, orgTitle, tagsToOrgString(self.tags), created)
            else:
                return "*{} {} {}\n{}\n{}\n".format(nesting, orgTitle, body, tagsToOrgString(self.tags), created)
        # If no body nor tags, note should be a single line
        else:
            return '*{} {}\n{}'.format(nesting, orgTitle, created)

def getAllNoteHtmlFiles(htmlDir):
    print('Looking for notes in {}'.format(htmlDir))
    noteHtmlFiles = []
    for root, dirs, files in os.walk(htmlDir):
        for file in files:
            if file.endswith('.html'):
                noteHtmlFiles.append(os.path.join(root, file))

    print ('Found {} notes'.format(len(noteHtmlFiles)))
    
    return noteHtmlFiles

def getHtmlValueIfMatches(line, tag, endTag):
    if tag.lower() in line.lower() and endTag.lower() in line.lower():
        return line[line.find(tag) + len(tag):-(len(endTag) + 1)], True
    
    return '', False

def makeSafeFilename(strToPurify):
    strToPurify = strToPurify.replace('/', '')
    strToPurify = strToPurify.replace('.', '')
    return strToPurify

def main(keepHtmlDir, outputDir):
    noteFiles = getAllNoteHtmlFiles(keepHtmlDir)

    noteGroups = {}
    
    for noteFilePath in noteFiles:
        # Read in the file
        noteFile = open(noteFilePath)
        noteLines = noteFile.readlines()
        noteFile.close()

        # print('Parsing {}'.format(noteFilePath))

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
                    
                # Parse title
                title, isMatch = getHtmlValueIfMatches(line, '<div class="title">', '</div>')
                if isMatch:
                    note.title = title
                    continue
                
                if '<div class="content">' in line:
                    readState = 'parsingBody'

                    # This isn't great; for same-line bodies, strip opening div
                    line = line.replace('<div class="content">', '')
                # Parse the date
                if ' AM</div>' in line or ' PM</div>' in line:
                    dateString = line.replace('</div>', '').strip()
                    # Example: "Apr 27, 2018, 6:32:15 PM"
                    note.date = datetime.datetime.strptime(dateString, '%b %d, %Y, %I:%M:%S %p')

                # Parse tags, if any
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

        # Add to groups based on tags
        for tag in note.tags:
            if tag in noteGroups:
                noteGroups[tag].append(note)
            else:
                noteGroups[tag] = [note]
        if not note.tags:
            if 'Untagged' in noteGroups:
                noteGroups['Untagged'].append(note)
            else:
                noteGroups['Untagged'] = [note]

    # We've parsed all the notes; write out the groups to separate .org files
    numNotesWritten = 0
    for tag, group in noteGroups.items():
        outFileName = '{}/{}.org'.format(outputDir, makeSafeFilename(tag))

        notesSortedByDate = sorted(group, key=lambda note: note.date)
        # If capture etc. appends, we should probably follow that same logic (don't reverse)
        # notesSortedByDate.reverse()

        # Concatenate all notes into lines
        lines = []
        archivedLines = []
        for note in notesSortedByDate:
            if note.archived:
                archivedLines.append(note.toOrgString() + '\n')
            else:
                lines.append(note.toOrgString() + '\n')
                
        if len(archivedLines):
            lines = ['* *Archived*\n'] + archivedLines + lines
        
        outFile = open(outFileName, 'w')
        outFile.writelines(lines)
        outFile.close()
        print('Wrote {} notes to {}'.format(len(group), outFileName))
        numNotesWritten += len(group)

    print('Wrote {} notes total'.format(numNotesWritten))

if __name__ == '__main__':
    if len(sys.argv) != 3:
        print('Wrong number of arguments!\nUsage:\n\tpython KeepToOrg.py /path/to/google/Keep output/dir')

    else:
        keepHtmlDir = sys.argv[1]
        outputDir = sys.argv[2]
        main(keepHtmlDir, outputDir)

