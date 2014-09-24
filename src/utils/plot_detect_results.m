function [ output_args ] = plot_detect_results( filename )
%PLOT_detect_results Summary of this function goes here
%   Detailed explanation goes here
set(0,'DefaultAxesFontName', 'Times New Roman')
set(0,'DefaultAxesFontSize', 22)

% Change default text fonts.
set(0,'DefaultTextFontname', 'Times New Roman')
set(0,'DefaultTextFontSize', 22)


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
    if std_data(1) == std_data(2)
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
    
h = figure();
plot(x_data, y_data);

title(title_str);
t = legend('Precision', 'Recall', 'F1 score','Location', 'southeast');
%set(t, 'FontSize', 50);

xlabel(x_label_str);
ylabel(y_label_str);
%set(findall(h, 'type', 'text'),'FontSize', 40, 'FontWeight', 'bold', 'FontName', 'Times New Roman');
axis tight;
out_filename = strcat(char(name), '.png');
saveas(h, fullfile(out_dir, out_filename));
 
TP = y_data(:,2) .* 1000;
P = TP ./ y_data(:, 1);
TPR = TP/1000;
FPR = (P - TP) ./ 9000;
FNR = (1000 - TP) ./ 1000;

% The FP/FN plot
h2 = figure();
plot(x_data, FPR, x_data, FNR);
title(title_str);
t = legend('False Positive', 'False Negative', 'Location', 'northeast');
xlabel(x_label_str);
ylabel(y_label_str);
axis tight;
out_filename = strcat(char(name), '.FPFN.png');
saveas(h2, fullfile(out_dir, out_filename));

% The ROC curve
h3 = figure();
plot(FPR, TPR, '-rx');
labels = cellstr( num2str(x_data) );
text(FPR(6:16), TPR(6:16), labels(6:16), 'color', 'r', 'VerticalAlignment','top',  'HorizontalAlignment','right');
t = legend(title_str, 'Location', 'southeast');

xlim([0.08,0.18])
ylim([0.99,1])
xlabel('False Positive Rate');
ylabel('True Positive Rate');
title(['ROC for ', x_label_str]);
%axis tight;
out_filename = strcat(char(name), '.ROC.png');
saveas(h3, fullfile(out_dir, out_filename));

end