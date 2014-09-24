function [ output_args ] = plot_stats( filename )
%PLOT_STATS Summary of this function goes here
%   Detailed explanation goes here
set(0,'DefaultAxesFontName', 'Times New Roman')
set(0,'DefaultAxesFontSize', 22)

% Change default text fonts.
set(0,'DefaultTextFontname', 'Times New Roman')
set(0,'DefaultTextFontSize', 22)


fid = fopen(filename);

% get the output directory
[pathstr, name, ext] = fileparts(filename);
out_dir = strcat( pathstr, '/figures/');
if ~exist(out_dir, 'dir')
  mkdir(out_dir);
end

% get the first three lines
title_str = fgetl(fid);

x_y_label = fgetl(fid);
labels = strsplit(x_y_label, ',');
x_label_str = char(labels(1));
y_label_str = char(labels(2));

legends = fgetl(fid);
legends_cell = strsplit(legends, ',');
legends_str = char(legends_cell);

x_data = [];
y_data = [];
while ~feof(fid)
    x_values = fgetl(fid);
    x = str2num(x_values);
    
    y_values = fgetl(fid);
    y_values = strsplit(y_values, ',');
    for k = 1:length(y_values)
        y(k) = str2num( char(y_values(k)) );
    end
    x_data = vertcat(x_data, x);
    y_data = vertcat(y_data, y);
end
x_data;
y_data;

h = figure('Name', title_str);
plot(x_data, y_data);

title(title_str);

t = legend(legends_str,'Location', 'southeast');
%set(t, 'FontSize', 50);

xlabel(x_label_str);
ylabel(y_label_str);
%set(findall(h, 'type', 'text'),'FontSize', 40, 'FontWeight', 'bold', 'FontName', 'Times New Roman');
axis tight;
out_filename = strcat(title_str, '.png');
saveas(h, fullfile(out_dir, out_filename));

end