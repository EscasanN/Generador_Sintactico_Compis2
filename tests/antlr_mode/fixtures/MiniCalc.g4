grammar MiniCalc;

root: expression EOF;
expression
    : expression '+' expression # AddExpression
    | expression '-' expression # SubtractExpression
    | INTEGER                   # IntegerExpression
    | STRING                    # StringExpression
    ;

INTEGER: [0-9]+;
STRING: '"' (~["\\\r\n] | '\\' .)* '"';
WS: [ \t\r\n]+ -> skip;
