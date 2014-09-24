function y=hex2uint64(x)
% Works similar to HEX2DEC but does not support multiple rows.
    
v=zeros(1,16);
y=uint64(0);

nibble=0;

for i=length(x):-1:1
    v=uint64(hex2dec(x(i)));
    v=bitshift(v,nibble);
    y=bitor(y,v);
    nibble=nibble+4;
end



