grammar MiniCalc;

root: expression EOF;
expression: INTEGER (('+' | '-') INTEGER)*;

INTEGER: [0-9]+;
WS: [ \t\r\n]+ -> skip;
