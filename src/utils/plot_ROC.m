function [ output_args ] = plot_ROC( input_args )
%PLOT_detect_results Summary of this function goes here
%   Detailed explanation goes here
set(0,'DefaultAxesFontName', 'Times New Roman')
set(0,'DefaultAxesFontSize', 22)

% Change default text fonts.
set(0,'DefaultTextFontname', 'Times New Roman')
set(0,'DefaultTextFontSize', 22)

filenames = {'data/test_10_13/test_list_10000_type_TEXT_DOM_std_c_1_20_h_3_14.eval',
    'data/test_10_13/test_list_10000_type_DOM_std_c_1_20_h_3_3.eval',
    'data/test_10_13/test_list_10000_type_TEXT_std_c_1_20_h_14_14.eval'};

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

std_data = [];
h_data = [];
y_data = [];

integration = 0;
while ~feof(fid)
    x_values = fgetl(fid);
    x_values = strsplit(x_values, ',');
    
    if (length(x_values) == 3)
    
    title_type = strsplit( char(x_values(1)), '=');
    title_type = str2num( char(title_type(2)) );

    std_constant = strsplit( char(x_values(2)), '=');
    std_constant = str2num( char(std_constant(2)) );
    h_threshold = strsplit( char(x_values(3)), '=');
    h_threshold = str2num( char(h_threshold(2)) );
    
    y_values = fgetl(fid);
    y_values = strsplit(y_values, ',');
    for k = 1:length(y_values)
        temp_y = strsplit( char(y_values(k)), '=');
        y(k) = str2num( char(temp_y(2)) );
    end
    std_data = vertcat(std_data, std_constant);
    h_data = vertcat(h_data, h_threshold);
    y_data = vertcat(y_data, y);
    
    elseif (length(x_values) == 5)
        integration = 1;
        std_constant = strsplit( char(x_values(5)), '=');
        std_constant = str2num( char(std_constant(2)) );
        
        y_values = fgetl(fid);
        y_values = strsplit(y_values, ',');
        for k = 1:length(y_values)
            temp_y = strsplit( char(y_values(k)), '=');
            y(k) = str2num( char(temp_y(2)) );
        end
        std_data = vertcat(std_data, std_constant);
        y_data = vertcat(y_data, y);
 
    end
end
std_data;
h_data;
y_data;

if integration == 0
    % label and legends
    if std_data(1) == std_data(2)ert
        x_label_str = 'Hamming Distance Threshold';
        x_data = h_data;
    else
        x_label_str = 'Standard Deviation Constant';
        x_data = std_data;
    end

    y_label_str = 'Evaluation';
    % legends_str = ['Precision', 'Recall', 'F1 score'];


    if title_type == 1
        title_str = 'Test on TEXT Simhash';
    elseif title_type == 2
        title_str = 'Test on DOM Simhash';
    end
else
    x_data = std_data;
    x_label_str = 'Standard Deviation Constant';
    y_label_str = 'Evaluation';
    title_str = 'Integration Test of TEXT and DOM Simhash';
end
 
TP = y_data(:,2) .* 1000;
P = TP ./ y_data(:, 1);
TPR = TP/1000;
FPR = (P - TP) ./ 9000;


mat_TPR = vertcat(mat_TPR, TPR');
mat_FPR = vertcat(mat_FPR, FPR');
mat_x_data = vertcat(mat_x_data, x_data');
mat_title_str = strvcat(mat_title_str, title_str);
end

% generate plots
h = figure();
p1 = plot(mat_FPR(1,:), mat_TPR(1,:), '-rx', mat_FPR(2,:), mat_TPR(2,:), '-gv', mat_FPR(3,:), mat_TPR(3,:), '-b<');
labels = mat_x_data(1,:)';
labels = cellstr( num2str(labels) );
labels
text(mat_FPR(1,4:13), mat_TPR(1,4:13), labels(4:13), 'color', 'r', 'VerticalAlignment','top',  'HorizontalAlignment','left');
text(mat_FPR(2,1:8), mat_TPR(2,1:8), labels(1:8), 'color', 'g', 'VerticalAlignment','top',  'HorizontalAlignment','left');
text(mat_FPR(3,4:13), mat_TPR(3,4:13), labels(4:13), 'color', 'b', 'VerticalAlignment','top',  'HorizontalAlignment','left');

%labels3 = cellstr( num2str(mat_x_data(3,:)) );
%mat_FPR(3,:)
%text(mat_FPR(3,:)', mat_TPR(3,:)', labels3', 'VerticalAlignment','top',  'HorizontalAlignment','left');


t = legend(mat_title_str, 'Location', 'southeast');
xlim([0,0.1])
ylim([0.9,1])
xlabel('False Positive Rate');
ylabel('True Positive Rate');
%title(strcat('ROC for ', x_label_str));
title(['ROC for ', x_label_str]);
%axis tight;
out_filename = strcat(char(name), '.ROC.png');
saveas(h, fullfile(out_dir, out_filename));

end

