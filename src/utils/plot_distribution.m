function [ output_args ] = plot_distribution( in, inter , title_str, legend_in, legend_inter)
%PLOT_DISTRIBUTION Summary of this function goes here
%   Detailed explanation goes here
x = in(:,1);
y = in(:,2);
h = figure();

plot(x, y, '-+r');    

%n = numel(x); % number of original points
%xi = interp1( 1:n, x, linspace(1, n, 10*n)); % new sample points 
%yi = interp1(   x, y, xi , 'spline');
hold all;
%plot( xi, yi ); % should be smooth between the original points


if ~isempty(inter)
    inter_x = inter(:,1);
    inter_y = inter(:,2);
    
    plot(inter_x, inter_y, '-*b');    
    %n = numel(inter_x); % number of original points
    %inter_xi = interp1( 1:n, inter_x, linspace(1, n, 10*n)); % new sample points 
    %inter_yi = interp1(   inter_x, inter_y, inter_xi , 'spline');
    hold all;
    %plot( inter_xi, inter_yi ); % should be smooth between the original points
    legend(legend_in, legend_inter);
end


title(title_str);
xlabel('Average Hamming Distance');
ylabel('Percentage');
axis tight;
end
