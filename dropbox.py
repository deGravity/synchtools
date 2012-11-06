#!/usr/bin/python
from collections import deque
import os
import shutil

class Rule:
    def __init__(self, dbfile, homefile, direction):
        self.dfile = dbfile
        self.hfile = homefile
        self.d = direction
    def covers(self, path):
        return self.dfile.startswith(path)
    def enforce(self, dropbox, home):
        dbfile = dropbox + '/' + self.dfile
        homefile = home + '/' + self.hfile
        if (self.d.startswith('left')):
            update(dbfile, homefile)
        else:
            update(homefile, dbfile)
        return

"""
There are many possible cases. tofile and fromefile can each be one of
realfile, linkedfile, nonexistant (1 2 3)

Cases (to,from)

1,1: merge from into to, delete from, create link(to,from)
1,2: All is good, nothing to do
1,3: create link(to,from)
2,1: delete to, move from to to, create link(to,from)
2,2: delete both, create empty to dir, createlink(to,from)
2,3: delete to, create empty to dir, createlink(to,from)
3,1: move from to to, createlink(to,from)
3,2: create empty to dir, delete from, createlink(to,from)
3,3: create empty to dir, createlink(to,from)

"""

def checklink(path):
    return os.path.islink(path)

def update(tofile, fromfile):
    tostate = 3
    fromstate = 3
    if (checklink(tofile)):
        tostate = 2
    elif (os.path.exists(tofile)):
        tostate = 1
    if (checklink(fromfile)):
        fromstate = 2
    elif (os.path.exists(fromfile)):
        fromstate = 1
    print( 'Updating ' + tofile + ' <- ' + fromfile + ' with state ' +
            str(tostate) +
            ',' + str(fromstate))
    deal(tofile, fromfile, tostate, fromstate)
    return

def deal(tofile, fromfile, tostate, fromstate):
    if tostate==1 and fromstate==2:
        return

    if tostate==1 and fromstate==3:
        createlink(tofile, fromfile)
        return

    if tostate==1 and fromstate==1:
        merge(fromfile, tofile)
        delete(fromfile)
        createlink(tofile, fromfile)

    if tostate==2 and fromstate==1:
        delete(tofile)
        merge(fromfile, tofile)
        delete(fromfile)
        createlink(tofile, fromfile)

    if tostate==2 and fromstate==2:
        delete(tofile)
        delete(fromfile)
        createdir(tofile)
        createlink(fromfile, tofile)

    if tostate==3 and fromstate==1:
        merge(tofile, fromfile) # Can actually just be a move to save time
        delete(fromfile) #Can be merged into above move
        createlink(tofile, fromfile)

    if tostate==3 and fromstate==2:
        createdir(tofile)
        delete(fromfile)
        createlink(tofile, fromfile)

    if tostate==3 and fromstate==3:
        createdir(tofile)
        createlink(tofile, fromfile)
    return

def createdir(d):
    print('Made directory ' + d)
    os.makedirs(d)
    return

def createlink(tofile, fromfile):
    print('Made link ' + fromfile + ' -> ' + tofile)
    frompath = fromfile[0:-(fromfile[::-1].find('/')+1)]
    print(frompath)
    if(not os.path.exists(frompath)):
        os.makedirs(frompath)
    os.symlink(tofile, fromfile)
    return


def deletelink(link):
    print('Deleted link at ' + link)
    os.unlink(link)
    return

def deletedir(d):
    print('Deleted directory ' + d)
    shutil.rmtree(d)
    return

def deletefile(f):
    print('Deleted file ' + f)
    os.remove(f)
    return

def delete(t):
    if (checklink(t)):
        deletelink(t)
    elif (os.path.isdir(t)):
        deletedir(t)
    else:
        deletefile(t)
    return

def mergefile(fromfile, intofile):
    print('Merged ' + fromfile + ' into ' + intofile)
    if (os.path.exists(intofile)):
        os.rename(intofile, intofile + '.OLD')
    shutil.copyfile(fromfile, intofile)
    return

# Pretty much ignores symlinks in general
# Does not account for either argument being a symlink
# Does not handle merging a file into a directory
def merge(fromdir, intodir):
    print('Merging ' + fromdir + ' into ' + intodir)
    if (os.path.isdir(fromdir)):
        if (not os.path.exists(intodir)):
            shutil.copytree(fromdir, intodir)
        else:
            files = os.listdir(fromdir)
            for f in files:
                merge(fromdir + '/' + f, intodir + '/' + f)
    elif (not checklink(fromdir) and os.path.exists(fromdir)):
        mergefile(fromdir, intodir)
    print('Finished Merging')
    return

def enforce(rules, dropbox, home):
    print('BEGINING CLEAN')
    cleandir(dropbox, rules, dropbox, home)
    print('CLEAN COMPLETED, BEGINNING ENFORCEMENT')
    for r in rules:
        r.enforce(dropbox, home)
    return

def cleandir(directory, rules, dropbox, home):
    files = os.listdir(directory)
    for f in files:
        fi = directory + '/' + f
        if iscovered(rules, fi[(len(dropbox)+1):]):
            if (os.path.isdir(fi)):
                cleandir(fi, rules, dropbox, home)
        elif (not os.path.islink(fi)):
            merge(fi, home + '/' + fi[len(dropbox)+1:])
            delete(fi)
    return

def iscovered(rules, path):
    for r in rules:
        if (r.covers(path)):
            return True
    return False

def readfile( file ):
    rules = deque()
    f = open(file, 'r')
    for line in f:
        rule = parse(line)
        if (rule ):
            rules.append(rule)
    f.close()
    return rules

def parse( line ):
    tags = 'true'
    rest = line
    if line.startswith('('):
        pos = 1
        count = 1
        while count > 0:
            if (line[pos] == '('):
                count = count + 1
            if (line[pos] == ')'):
                count = count - 1
            pos = pos + 1
        tags = parsetags(line[0:pos])
        rest = line[pos:]
    if tags:
        rest = rest.strip()
        direction = 'left'
        if (rest.find('<-') > 0):
            parts = rest.split('<-')
        elif (rest.find('->') > 0):
            parts = rest.split('->')
            direction = 'right'
        else:
            parts = [rest, rest]
        return Rule( parts[0].strip(), parts[1].strip(), direction)
    return False

def gettags():
    env = {'true':True, 'false':False}
    return env

def checktag(tag, env):
    return env.get(tag,False)

def parsetags( tags ):
    env = gettags()
    currtoken=''
    tokens = deque()
    stack = deque()
    output = deque()
    # Tokenize input
    for c in tags:
        if c==' ':
            env = env
        elif c=='(' or c==')' or c=='&' or c=='|':
            if currtoken != '':
                tokens.append(currtoken)
                currtoken = ''
            tokens.append(c)
        else:
            currtoken = currtoken + c
    while( tokens ):
        t = tokens.popleft()
        if t=='(':
            stack.append(t)
        elif t==')':
            tt = stack.pop()
            while tt != '(':
                v1 = output.pop()
                v2 = output.pop()
                if tt=='&':
                    output.append(v1 and v2)
                else:
                    output.append(v1 or v2)
                tt = stack.pop()
        elif t=='&':
            tt = stack.pop()
            while tt == '&' or tt == '|':
                v1 = output.pop()
                v2 = output.pop()
                if tt == '&':
                    output.append(v1 and v2)
                else:
                    output.append(v1 or v2)
                tt = stack.pop()
            stack.append(tt)
            stack.append(t)
        elif t=='|':
            tt = stack.pop()
            while tt == '|':
                v1 = output.pop()
                v2 = output.pop()
                output.append(v1 or v2)
            stack.append(tt)
            stack.append(t)
        else:
            output.append(checktag(t, env))
    return output.pop()

def test():
    rules = readfile('homedir.rc')
    enforce(rules, '/Users/ben/Projects/Organization/dropbox', '/Users/ben/Projects/Organization/home')
