from PyTib.common import open_file, write_file, pre_process
import os
import re
from collections import defaultdict
import csv
import pickle
import regex


def is_punct(string):
    """returns False at the first character that is not a punctuation in the list, else True"""
    puncts = ['༄', '༅', '༆', '༇', '༈', '།', '༎', '༏', '༐', '༑', '༔', '_']
    for char in string:
        if char not in puncts:
            return False
    return True


def punct_view(prepared):
    """keeps all the punctuation and replaces syllables either by dashes(count=False) or by a number(count=True)"""
    out = []
    for el in prepared:
        if type(el) == str and el != '':
            out.append(el)
        elif type(el) == tuple:
            dashes = ['-' for a in range(int(el[1]/2))]
            new = dashes + [str(el[1])] + dashes
            out.append(''.join(new))
    return out


def preprocess(string):
    """a list of punctuation and paragraphs. punctuations are strings, paragraphs are splitted in a list of syls."""
    #
    splitted = re.split(r'\n+', string)
    joined = ''.join([a+'-' if is_punct(a[-1]) else a for a in splitted])

    processed = []
    paragraphs = pre_process(joined, mode='words')
    for a in paragraphs:
        if a != '-' and not is_punct(a):
            syls = pre_process(a, mode='syls')
            par_len = len(syls)
            first_syl = syls[0]
            last_syl = syls[-1]
            processed.append((first_syl, par_len, last_syl))
        elif a != '-':
            processed.append(a)
    return processed


def create_missing_dir(path):
    """creates the folder designated in path if it does not exist"""
    if not os.path.exists(path):
        os.makedirs(path)


def write_output(output, out_path, output_type):
    """
    writes the output found in the
    :param output: content to be written
    :param out_path: where to write
    :param output_type: name of the containing folder and output file suffix
    :return: writes files to the corresponding folder
    """
    out_dir = '{}/{}'.format(out_path, output_type)
    create_missing_dir(out_dir)
    for vol, out in output.items():
        write_file('{}/{}_{}.txt'.format(out_dir, vol, output_type), ' '.join(out))


def format_punct_types(punct_types):
    """sort the punct types by reversed frequency"""
    formatted = []
    sorted_keys = sorted(punct_types.keys(), key=lambda x: punct_types[x], reverse=True)
    for key in sorted_keys:
        formatted.append('“{}”\t{}'.format(key, punct_types[key]))
    return '\n'.join(formatted)


def find_punct_types(collection):
    """counts the overall frequency of each punct type for the whole collection"""
    types = defaultdict(int)
    for vol, prepared in collection.items():
        for a in prepared:
            if type(a) == str:
                types[a] += 1
    return types


def missing_dirs():
    """create the dirs in the list if they are missing"""
    for dir in ['input', 'cache', 'output']:
        create_missing_dir(dir)


def prepare_collection(in_path):
    """wrapper function """
    collection = {}
    for f in os.listdir(in_path):
        vol_name = f.split('.')[0]
        raw = open_file('{}/{}'.format(in_path, f)).strip()
        # pre-processing
        collection[vol_name] = preprocess(raw)
    return collection


def collection_dots(collection):
    all_dots = {}
    for vol, prepared in collection.items():
        all_dots[vol] = punct_view(prepared)
    return all_dots


def open_prepared(in_path):
    cache_name = in_path.split('/')[-1]
    cache_file = 'cache/{}_pre_processed.p'.format(cache_name)
    if os.path.isfile(cache_file):
        prepared_vols = pickle.load(open(cache_file, 'rb'))
    else:
        prepared_vols = prepare_collection(in_path)
        pickle.dump(prepared_vols, open(cache_file, 'wb'))
    return prepared_vols


def full_text_conc(in_path, vol_name, punct):
    full_vol = open_file('{}/{}'.format(in_path, vol_name))
    conc = regex.search(punct, full_vol)
    conc.detach_string()
    return conc


def punct_conc(punct, prepared, in_path):
    concs = []
    for vol_name, volume in prepared.items():
        if punct in volume:
            for num, el in enumerate(volume):
                if el == punct:
                    if num-1 > 0:
                        left = volume[num - 1]
                    else:
                        left = 'start'
                    if num+1 < len(volume):
                        right = volume[num + 1]
                    else:
                        right = 'end'

                    # if there is a tuple, format to have only the syllables around the punct
                    if type(left) == tuple:
                        left = '--{}--{}'.format(left[1], left[2])
                    if type(right) == tuple:
                        right = '{}--{}--'.format(right[0], right[1])

                    # find the full text concordance
                    full_conc = full_text_conc(in_path, vol_name, punct)
                    concs.append((left, el, right, full_conc, vol_name))
    return concs


def concs_by_freq(prepared, in_path, all_puncts, frequency):
    all_concs = []
    for punct, freq in all_puncts.items():
        if freq <= frequency:
            conc = punct_conc(punct, prepared, in_path)
            all_concs.append((punct, conc))
    return all_concs


def main():
    in_path = '../Derge-Kangyur-raw/ekangyur_raw'  # default is 'input'
    out_path = 'output'
    missing_dirs()

    # pre-processing
    print('loading the collection')
    prepared_vols = open_prepared(in_path)
    # counting
    print('counting the punctuation types')
    punct_types = find_punct_types(prepared_vols)

    # processing
    #print('generating "with dots" data')
    dots = collection_dots(prepared_vols)

    concordances = concs_by_freq(prepared_vols, in_path, punct_types, 1)

    # save results
    print('writing outputs')
    write_output(dots, out_path, 'with_dots')

    write_file('{}/total_types.txt'.format(out_path), format_punct_types(punct_types))


if __name__ == '__main__':
    main()
