function [ output_args ] = plot_clusters( filename )
%PLOT_CLUSTERS Summary of this function goes here
%   Detailed explanation goes here
%
%   To Run:
%       plot_clusters('train13_test24/plot_clusters_md_9_mcz_2_sw_1_tw_1');

fid = fopen(filename);
label_md5_map = containers.Map();
label_md5_map_filename = strcat(filename, '_label_md5_map');
label_md5_map_fid = fopen(label_md5_map_filename, 'w');

% get the output directory
[pathstr, name, ext] = fileparts(filename);
out_dir = strcat( pathstr, '/figures/');
in_filename = name
if ~exist(out_dir, 'dir')
  mkdir(out_dir);
end

% read clusters
tline = '0';
SIMHASH_SIZE = 64;

md5_opt.Input = 'bin';
md5_opt.Method = 'MD5';
md5_opt.Format = 'HEX';

while ~feof(fid)
    tline = fgetl(fid);
    disp(tline)
    C = strsplit(tline, ',');
    label = char(C(1));
    label_md5 = DataHash(uint8(label), md5_opt);
    label_md5_map(label) = label_md5;

    count = str2num(char(C(2)));
    data = zeros(count, SIMHASH_SIZE);
    for n = 1:count
        tline = fgetl(fid);
        simhash = hex2uint64(tline);
        bin_vector = dec2bin(hex2dec(tline))=='1';
        length = size(bin_vector);
        length = length(2);
        if length < SIMHASH_SIZE
            data(n, 1:SIMHASH_SIZE-length) = zeros(1, SIMHASH_SIZE-length);
            data(n, SIMHASH_SIZE-length+1:end) = bin_vector;
        else
            data(n,:) = bin_vector;
        end
    end
    data = data * 20;
    h = figure('Name', label_md5);
    set(gcf, 'Visible', 'off');
    image(data);
    title(label_md5);
    xlabel('bits');
    ylabel('simhashs');
    
    out_filename = strcat(in_filename, '_', label_md5, '.png');
    saveas(h, fullfile(out_dir, out_filename));
end
labels = keys(label_md5_map);
labels_md5 = values(label_md5_map);
for n = 1:size(labels, 2)
    fprintf(label_md5_map_fid, '%s,%s\n', labels_md5{n}, labels{n});
end
fclose(label_md5_map_fid);
end


