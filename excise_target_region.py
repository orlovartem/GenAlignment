import argparse
import os
import sys
import subprocess
import pandas as pd
from Bio import SeqIO
from Bio import AlignIO


def find_target_region(input_file, reference, rstart, rend, path_to_blast):
    '''
    Performs standalone blast of sequences from input_file against reference sequence.
    Check whether sequence from input_file overlaps with region [rstart,rend] in reference sequences

    Input:
        input_file - name of file with sequence alignment, fasta format
        reference - name of file with reference, fasta format
        rstart - start position of segment in reference seq
        rstart - end position of segment in reference seq
        output_dir - output directory to save fasta file with sequences that overlap with target region
    '''

    output_dir = os.path.split(input_file)[0] # '/'.join(input_file.split('/')[:-1])+'/'

    # start and end positions of target region in reference sequence
    global start
    start = rstart
    global end
    end = rend

    records = list(SeqIO.parse(input_file, "fasta"))

    seq_ordered = []
    for rec in records:
        seq_ordered.append(rec.id)
    # print('{}makeblastdb.exe -in {} -dbtype nucl -out {}local_db'.format(path_to_blast, reference,output_dir))

    # print('{}blastn.exe -db local_db -query {} -outfmt 6 -out {}blast.out \
    #                                    -strand plus -evalue 1e-20'.format(path_to_blast, input_file, output_dir))
    
    out_path_db = str(os.path.join(output_dir,'local_db'))
    out_path_blast = str(os.path.join(output_dir,'blast.out'))
    if sys.platform == 'win32' or sys.platform == 'cygwin':
        makeblast_command = '{}makeblastdb.exe -in {} -dbtype nucl -out {}'.format(path_to_blast,
                                                                                    reference,
                                                                                    out_path_db)
        blastn_command = '{blast_path}blastn.exe -db {out_db} -query {input} -outfmt 6 -out \
                            {out_blast} -strand plus -evalue 1e-20 -word_size 7'.format(blast_path=path_to_blast,
                                                                                        input=input_file,
                                                                                        out_db=out_path_db,
                                                                                        out_blast=out_path_blast)
    else:
        makeblast_command = '{}makeblastdb -in {} -dbtype nucl -out {}'.format(path_to_blast,
                                                                                reference,
                                                                                out_path_db)
        blastn_command = '{blast_path}blastn -db {out_db} -query {input} -outfmt 6 -out \
                            {out_blast} -strand plus -evalue 1e-20 -word_size 7'.format(blast_path=path_to_blast,\
                                                                                        input=input_file,
                                                                                        out_db=out_path_db,
                                                                                        out_blast=out_path_blast)
    # creating local database using reference sequence
    subprocess.call(makeblast_command, shell=True)

    # blast against reference sequences
    subprocess.call(blastn_command, shell=True)

    # dataframe with blast results
    blast_output = pd.read_csv(out_path_blast, sep='\t', header = None, \
                                names=['qseqid','sseqid','pident','length','mismatch',\
                                'gapopen','qstart','qend','sstart','send','evalue','bitscore'])

    blast_output =blast_output.join(pd.Series(name="overlap")) # adds "overlap" column
    blast_output = blast_output.apply(check_overlap, axis = 1) # checks whether each blast alignment overlaps with target regions

    seq_names = list(blast_output.loc[blast_output['overlap'] == 1, 'qseqid']) # names of seqs which overlap with target region

    output_file =  os.path.join(output_dir, os.path.splitext(input_file)[0] + '_exc.fasta') # name of output file

    in_al = SeqIO.to_dict(SeqIO.parse(input_file, "fasta")) # dictionary with sequences in input_file
    out_al = [] # list with sequences which contain target region
    for key in seq_ordered:
        if key in seq_names:
            out_al.append(in_al[key])
    SeqIO.write(out_al, output_file, "fasta") # writing output fasta-file
    
    return(output_file)

def check_overlap(col):
    '''
    Checks whether to segments overlap
    Input:
        col - pd.Series -  a column in dataframe which contains blast results
        col['sstart'] - start of aligned region identified by blast
        col['ssend'] - end of aligned region identified by blast
    Output:
        Returns col
        col['overlap'] = 1 if segment [start,end] and [col['sstart'],col['send']] overlap
        start, end are start and end positions of target region in reference sequence, global
        
    '''

    # start and end positions of alignment in reference genome
    sstart = int(col['sstart'])
    send = int(col['send'])

    l1 = col['length'] / (end - start + 1)
    l2 = ((end - sstart + 1) / (end - start + 1))
    l3 = ((send - start + 1) / (end - start + 1))

    inside = start >= sstart and end <= send # target region is inside alignment

    # left = start <= sstart and sstart <= end and ((end - sstart+1) / (end - start + 1))>0.9
    left = sstart <= end and end <= send and ((end - sstart + 1) / (end - start + 1))>0.9

    # right  = start <= send and send <= end and ((send - start +1) / (end - start + 1))>0.9 
    right = sstart <= start and start <=send  and ((send - start + 1) / (end - start + 1))>0.9

    #target region is larger than alignment
    larger = start <= sstart and end >= send and col['length'] / (end - start + 1)>0.9 

    if inside or left or right or larger:
        col['overlap'] = 1

    return col



if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-input", "--input_file", type=str,
                        help="Input file",
                        required=True)
    parser.add_argument("-ref", "--reference", type=str,
                        help="File with reference sequence in fasta-format",
                        required=True)
    parser.add_argument("-s", "--start", type=int,
                        help="Start position of region of interest in reference sequence",
                        required=True)
    parser.add_argument("-e", "--end", type=int,
                        help="End position of region of interest in reference sequence",
                        required=True)
    parser.add_argument("-path_blast", "--path_blast", type=str,
                        help="Path to blast",
                        required=True)
    args = parser.parse_args()

    find_target_region(args.input_file,
                        args.reference,
                        args.start,
                        args.end,
                        args.path_blast)
