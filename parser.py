#!/usr/bin/env python
# -*- encoding: utf-8 -*-
from __future__ import print_function

import os
from optparse import OptionParser
from binascii import crc32
import logging

try:
  import kaa.metadata
except ImportError:
    print('kaa.metadata is not available. Please install python-kaa-metadata.')
    exit()
except DeprecationWarning:
    pass

try:
    from jinja2 import Environment, FileSystemLoader
except ImportError:
    print('jinja2 is not available. Please install python-jinja2.')
    exit()

__version__ = '1.0'

logger = logging.getLogger()

#logging to stdout
formatter = logging.Formatter('%(levelname)s %(module)s'+\
                              '(%(lineno)s): %(message)s')
handler = logging.StreamHandler()
handler.setFormatter(formatter)
logger.addHandler(handler)

#set log level
logger.setLevel(logging.WARNING)

logger = logging.getLogger('metadata')


def printCLI(data):
    from string import Template
    s = Template(u"""
        Nom du fichier: $filename
        Extension: $extension
        Taille: $size Mo
        Codec video / audio: $vcodec, $acodec
        Résolution: $width x $height
        CRC32: $crc32
        Lien DDL: N/A
        """)
    if type(data) is not type(list()):
        print(s.substitute(data))
    else:
        for mfile in data:
            print(s.substitute(mfile))
            print('-*'*10 + '-')
    

def formatHTML(data, output=None):
    from datetime import datetime

    date = str( datetime.utcnow().strftime("%c UTC") )

    env = Environment(loader=FileSystemLoader(os.path.abspath('./templates')))
    myTpl = env.get_template('element.html')
    if output is not None:
        output = os.path.abspath(output)
        outputDir = os.path.dirname(output)
        if not os.path.exists(outputDir):
            os.mkdir(outputDir, 0755)
        print('Rendering html into {0}'.format(output))
        myTpl.stream(medias=data, date=date).dump(output, encoding='utf-8')
    else:
        print(myTpl.render(medias=data, date=date))



def parse_file(currentFile):
    print('Computing {0} ...'.format(os.path.basename(currentFile)),
          end='        ')
    rawinfo = kaa.metadata.parse(currentFile)
    if rawinfo is None:
        print('IGNORED')
        return
    elif rawinfo.media == 'MEDIA_AV':
        info = dict({'type': rawinfo.type,
                     'length': rawinfo.length,
                     'vcodec': rawinfo.video[0].codec,
                     'height': rawinfo.video[0].height,
                     'width': rawinfo.video[0].width,
                     'acodec': rawinfo.audio[0].codec})
    elif rawinfo.media == 'MEDIA_AUDIO':
        print('IGNORED')
        return
        #info = dict({'type': rawinfo.type,
        #             'length': rawinfo.length,
        #             'acodec': rawinfo.codec})
    else:
        logger.warning('Unsupported media format: {0}'.format(rawinfo.media))

    with open(currentFile, 'r') as f:
        prev = 0
        for eline in f:
            prev = crc32(eline, prev)
        mcrc32 = format(prev & 0xFFFFFFFF, '08x')

    info.update({'filename': os.path.basename(currentFile),
                 'size': os.path.getsize(currentFile)/1024/1024,
                 'extension': os.path.basename(currentFile)[-3:],
                 'crc32': mcrc32})
    print('DONE')
    return info

def main():
    parser = OptionParser(version='%prog 1.0')
    parser.add_option('-d', '--directory', action='store', type='string',
                      metavar='DIRECTORY', help="Parse files in DIRECTORY.")
    parser.add_option('-f', '--file', action='store', type='string',
                      metavar='FILE', help='Parse media file FILE for metadata.')
    parser.add_option('--html', action='store_true', dest='generate_html',
                      help='Generate html table instead of standard text.')
    parser.add_option('-o', '--output', action='store', type='string', default=None,
                      metavar='FILE', help='write output to FILE')
    parser.add_option('--verbose', action='store_true', default=True,
                      help='Print everything this thing is doing.')

    (options, args) = parser.parse_args()

    if options.verbose:
        logger.setLevel(logging.INFO)

    if options.directory is not None:
        mdirectory = os.path.abspath(options.directory)
        dirlist = os.listdir(mdirectory)
        dirlist.sort()
        dirInfo = list()
        for directoryContent in dirlist:
            if os.path.isdir(mdirectory + '/' + directoryContent):
                logger.info('Ignoring subdirectory {0}'.format(directoryContent))
                continue
            elif os.path.isfile(mdirectory + '/' + directoryContent):
                data = parse_file(mdirectory + '/' + directoryContent)
                if data is not None:
                    dirInfo.append(data)
            else:
                logging.warning('Can\'t stat {0}'.format(mdirectory + '/' + directoryContent))
    elif options.file is not None:
        mfile = os.path.abspath(options.file)
        dirInfo = parse_file(mfile)
    else:
        parser.error('No file nor directory given.')

    if options.generate_html:
        if type(dirInfo) is not type(list()):
            dirInfo = [dirInfo]
        formatHTML(dirInfo, options.output)
    else:
        printCLI(dirInfo)

if __name__ == '__main__':
    main()