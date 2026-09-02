grammar TinyNumber;

start: value EOF;
value: INTEGER # WholeNumber;

INTEGER: [0-9]+;
WS: [ \t\r\n]+ -> skip;
