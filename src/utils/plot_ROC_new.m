function [ output_args ] = plot_ROC_new( input_args )
%UNTITLED3 Summary of this function goes here
%   Detailed explanation goes here

filenames = {'../../data/train/train_dom_plot_ROC',
    '../../data/train/train_text_plot_ROC',
    '../../data/train/train_integrated_plot_ROC_new_text_r_15.0',
    '../../data/train/train_integrated_plot_ROC_new_text_r_17.0',
    '../../data/train/train_integrated_plot_ROC_new_text_r_19.0'};
    %'data/test_10_13/test_list_10000_type_TEXT_std_c_1_20_h_14_14.eval'};

mat_TPR = [];
mat_FPR = [];
mat_x_data = [];
mat_title_str = [];
for index = 1:numel(filenames)
    filename = filenames{index};
    filename

fid = fopen(filename);
% get the output directory
% get the output directory
[pathstr, name, ext] = fileparts(filename);
out_dir = strcat( pathstr, '/figures/');
if ~exist(out_dir, 'dir')
  mkdir(out_dir);
end

train_c_data = [];
test_c_data = [];
test_d_data = [];
y_data = [];

if ~isempty(strfind(filename, 'integrated'))
    filename
    text_radius_str = strsplit(filename, '_');
    text_radius_str = char(text_radius_str(end));
    legend_str = strcat('R_{detect, text} = ', ...
        text_radius_str, ', R_{detect, dom}');
elseif ~isempty(strfind(filename,'dom'))
    legend_str = 'R_{detect, dom}';
elseif ~isempty(strfind(filename,'text'))
    legend_str = 'R_{detect, text}';
else
    legend_str = 'Integration of Dom and Text Simhash';
end

while ~feof(fid)
    x_values = fgetl(fid);
    x_values = strsplit(x_values, ',');
    %title_type = strsplit( char(x_values(1)), '=');
    %title_type = str2num( char(title_type(2)) );

    %train_coefficient = strsplit( char(x_values(2)), '=');
    train_coefficient = str2num( char(x_values(1)) );
    test_coefficient = str2num( char(x_values(2)) );
    test_diameter = str2num( char(x_values(3)) );
    
    y_values = fgetl(fid);
    y_values = strsplit(y_values, ',');
    for k = 1:length(y_values)
        y(k) = str2num( char(y_values(k)) );
    end
    train_c_data = vertcat(train_c_data, train_coefficient);
    test_c_data = vertcat(test_c_data, test_coefficient);
    test_d_data = vertcat(test_d_data, test_diameter);
    y_data = vertcat(y_data, y);
end
train_c_data;
test_c_data;
test_d_data;
y_data;

%title_str = 'R_{detect, text} and Text R_{detect, dom}';
title_str = legend_str;
x_label_str = 'Minimum Radius';
y_label_str = 'Evaluation';
x_data = test_d_data;

 
%TP = y_data(:,2) .* 1000;
%P = TP ./ y_data(:, 1);
%TPR = TP/1000;
%FPR = (P - TP) ./ 9000;


mat_TPR = vertcat(mat_TPR, y_data(:,1)');
mat_FPR = vertcat(mat_FPR, y_data(:,2)');
mat_x_data = vertcat(mat_x_data, x_data');
mat_title_str = strvcat(mat_title_str, title_str);
end

% generate plots
h = figure();
mat_TPR;
mat_FPR;
% plot -> semilogx
p1 = semilogx(mat_FPR(1,:), mat_TPR(1,:), '-rx', mat_FPR(2,:), mat_TPR(2,:), '-go', ...
    mat_FPR(3,:), mat_TPR(3,:), ':k', mat_FPR(4,:), mat_TPR(4,:), '--c', ...
    mat_FPR(5,:), mat_TPR(5,:), '-.b');
    %mat_FPR(3,:), mat_TPR(3,:), ':ks', mat_FPR(4,:), mat_TPR(4,:), '-cd', ...
    %mat_FPR(5,:), mat_TPR(5,:), '-b<');
    
labels = mat_x_data(1,:)';
labels = cellstr( num2str(labels) );
labels
text(mat_FPR(1,14:14), mat_TPR(1,14:14), labels(14:14), 'color', 'r', ...
    'VerticalAlignment','top',  'HorizontalAlignment','left', ...
    'FontSize', 16, 'FontName','Times New Roman');
text(mat_FPR(2,14:14), mat_TPR(2,14:14), labels(14:14), 'color', 'g', ...
    'VerticalAlignment','top',  'HorizontalAlignment','right', ...
    'FontSize', 16, 'FontName','Times New Roman');
text(mat_FPR(3,14:14), mat_TPR(2,14:14), ...
    strcat(labels(14:14), ' (0.3%, 97.1%)'), ...
    'color', 'k', ...
    'VerticalAlignment','bottom',  'HorizontalAlignment','left', ...
    'FontSize', 16, 'FontName','Times New Roman');
hold on;
semilogx([0.0000001 mat_FPR(3,14)], [mat_TPR(3, 14:14) mat_TPR(3, 14:14)], '-k');
hold on;
semilogx([mat_FPR(3,14) mat_FPR(3,14)], [0.5 mat_TPR(3, 14:14)], '-k');

mat_TPR(3, 14:14)
mat_FPR(3,14:14)

t = legend(mat_title_str, 'Location', 'southeast');
hx = xlabel('False Positive Rate (log scale)');
hy = ylabel('True Positive Rate');
%title(strcat('ROC for ', x_label_str));
ht = title(['ROC for ', x_label_str]);

set([ht, hx, hy, t], 'FontSize', 20, 'FontName','Times New Roman');
set(gca, 'XLim',[5 * 10^-4 1], 'YLim',[0.5 1], 'GridLineStyle','-', ...
    'XGrid','on','YGrid','on', 'FontSize', 18, 'FontName','Times New Roman');


%axis tight;
out_filename = strcat(char(name), '.svg');
saveas(h, fullfile(out_dir, out_filename));

end


