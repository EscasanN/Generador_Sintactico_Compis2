grammar Compiscript;

// ------------------
// Parser Rules
// ------------------
//
// NOTA DE DISEÑO (bloque 4 -- Nelson, ver docs/phase3/REGLAS_Y_DECISIONES.md):
// El perfil semantico (semantic_profiles/compiscript.semantic.json) solo puede
// seleccionar hijos de un nodo por indice fijo, por tipo de token directo, o por
// texto concatenado del nodo actual. No existe un selector que aplane listas de
// aridad variable ni que dependa de que alternativa opcional se uso. Por eso,
// toda regla que en el ejemplo original combinaba varias partes opcionales
// (X? Y?) se dividio aqui en alternativas etiquetadas de aridad fija -- misma
// gramatica superficial, mismo lenguaje aceptado, arbol de derivacion mas
// regular. Los cambios estan documentados con fecha en REGLAS_Y_DECISIONES.md.

program: statement* EOF;

statement
  : variableDeclaration
  | constantDeclaration
  | assignment
  | functionDeclaration
  | classDeclaration
  | expressionStatement
  | printStatement
  | block
  | ifStatement
  | whileStatement
  | doWhileStatement
  | forStatement
  | foreachStatement
  | tryCatchStatement
  | switchStatement
  | breakStatement
  | continueStatement
  | returnStatement
  ;

block: '{' statement* '}';

variableDeclaration
  : ('let' | 'var') Identifier ';'                                   # VarNoTypeNoInit
  | ('let' | 'var') Identifier typeAnnotation ';'                    # VarTypeNoInit
  | ('let' | 'var') Identifier initializer ';'                       # VarNoTypeInit
  | ('let' | 'var') Identifier typeAnnotation initializer ';'        # VarTypeInit
  ;

constantDeclaration
  : 'const' Identifier '=' expression ';'                            # ConstNoType
  | 'const' Identifier typeAnnotation '=' expression ';'             # ConstWithType
  ;

typeAnnotation: ':' type;
initializer: '=' expression;

assignment
  : Identifier '=' expression ';'                                    # SimpleAssignment
  | expression '.' Identifier '=' expression ';'                     # PropertyAssignment
  ;

expressionStatement: expression ';';
printStatement: 'print' '(' expression ')' ';';

ifStatement
  : 'if' '(' expression ')' block                                    # IfNoElse
  | 'if' '(' expression ')' block 'else' block                       # IfWithElse
  ;

whileStatement: 'while' '(' expression ')' block;
doWhileStatement: 'do' block 'while' '(' expression ')' ';';

forInit: variableDeclaration | assignment | ';';

forStatement
  : 'for' '(' forInit ';' ')' block                                  # ForNoCondNoUpdate
  | 'for' '(' forInit expression ';' ')' block                       # ForCondNoUpdate
  | 'for' '(' forInit ';' expression ')' block                       # ForNoCondUpdate
  | 'for' '(' forInit expression ';' expression ')' block            # ForCondUpdate
  ;

foreachStatement: 'foreach' '(' Identifier 'in' expression ')' block;
breakStatement: 'break' ';';
continueStatement: 'continue' ';';

returnStatement
  : 'return' ';'                                                     # ReturnVoid
  | 'return' expression ';'                                          # ReturnValue
  ;

tryCatchStatement: 'try' block 'catch' '(' Identifier ')' block;

switchStatement: 'switch' '(' expression ')' '{' switchCase* defaultCase? '}';
switchCase: 'case' expression ':' statement*;
defaultCase: 'default' ':' statement*;

functionDeclaration
  : 'function' Identifier '(' ')' block                              # FunctionNoParamsNoReturn
  | 'function' Identifier '(' parameters ')' block                   # FunctionWithParamsNoReturn
  | 'function' Identifier '(' ')' ':' type block                     # FunctionNoParamsWithReturn
  | 'function' Identifier '(' parameters ')' ':' type block          # FunctionWithParamsWithReturn
  ;

parameters
  : parameters ',' parameter                                         # MoreParameters
  | parameter                                                        # FirstParameter
  ;

parameter
  : Identifier ':' type                                              # TypedParameter
  | Identifier                                                       # UntypedParameter
  ;

classDeclaration
  : 'class' Identifier '{' classMember* '}'                          # ClassNoSuper
  | 'class' Identifier ':' Identifier '{' classMember* '}'           # ClassWithSuper
  ;

classMember: classMethod | classField | classConstant;

classMethod
  : 'function' Identifier '(' ')' block                              # MethodNoParamsNoReturn
  | 'function' Identifier '(' parameters ')' block                   # MethodWithParamsNoReturn
  | 'function' Identifier '(' ')' ':' type block                     # MethodNoParamsWithReturn
  | 'function' Identifier '(' parameters ')' ':' type block          # MethodWithParamsWithReturn
  ;

classField
  : ('let' | 'var') Identifier ';'                                   # FieldNoTypeNoInit
  | ('let' | 'var') Identifier typeAnnotation ';'                    # FieldTypeNoInit
  | ('let' | 'var') Identifier initializer ';'                       # FieldNoTypeInit
  | ('let' | 'var') Identifier typeAnnotation initializer ';'        # FieldTypeInit
  ;

classConstant
  : 'const' Identifier '=' expression ';'                            # ConstFieldNoType
  | 'const' Identifier typeAnnotation '=' expression ';'             # ConstFieldWithType
  ;

// ------------------
// Expression Rules -- Operator Precedence
// ------------------

expression: assignmentExpr;

assignmentExpr
  : lhs=leftHandSide '=' assignmentExpr                # AssignExpr
  | lhs=leftHandSide '.' Identifier '=' assignmentExpr # PropertyAssignExpr
  | conditionalExpr                                    # ExprNoAssign
  ;

conditionalExpr
  : logicalOrExpr '?' expression ':' expression        # TernaryExpr
  | logicalOrExpr                                      # ConditionalAtom
  ;

logicalOrExpr
  : logicalOrExpr '||' logicalAndExpr                  # OrExpr
  | logicalAndExpr                                     # LogicalOrAtom
  ;

logicalAndExpr
  : logicalAndExpr '&&' equalityExpr                   # AndExpr
  | equalityExpr                                       # LogicalAndAtom
  ;

equalityExpr
  : equalityExpr '==' relationalExpr                   # EqualsExpr
  | equalityExpr '!=' relationalExpr                   # NotEqualsExpr
  | relationalExpr                                     # EqualityAtom
  ;

relationalExpr
  : relationalExpr '<' additiveExpr                    # LessExpr
  | relationalExpr '<=' additiveExpr                   # LessEqualExpr
  | relationalExpr '>' additiveExpr                    # GreaterExpr
  | relationalExpr '>=' additiveExpr                   # GreaterEqualExpr
  | additiveExpr                                       # RelationalAtom
  ;

additiveExpr
  : additiveExpr '+' multiplicativeExpr                # AddExpr
  | additiveExpr '-' multiplicativeExpr                # SubExpr
  | multiplicativeExpr                                 # AdditiveAtom
  ;

multiplicativeExpr
  : multiplicativeExpr '*' unaryExpr                   # MulExpr
  | multiplicativeExpr '/' unaryExpr                   # DivExpr
  | multiplicativeExpr '%' unaryExpr                   # ModExpr
  | unaryExpr                                          # MultiplicativeAtom
  ;

unaryExpr
  : '-' unaryExpr                                      # NegExpr
  | '!' unaryExpr                                      # NotExpr
  | primaryExpr                                        # UnaryAtom
  ;

primaryExpr
  : literalExpr                                        # LiteralPrimary
  | leftHandSide                                       # LeftHandSidePrimary
  | '(' expression ')'                                 # ParenPrimary
  ;

literalExpr
  : IntegerLiteral                                     # IntegerLiteralExpr
  | StringLiteral                                      # StringLiteralExpr
  | arrayLiteral                                       # ArrayLiteralExpr
  | 'null'                                             # NullLiteral
  | 'true'                                             # TrueLiteral
  | 'false'                                            # FalseLiteral
  ;

leftHandSide
  : primaryAtom                                        # LeftHandSideAtom
  | leftHandSide '(' ')'                               # CallExprNoArgs
  | leftHandSide '(' argumentList ')'                  # CallExprWithArgs
  | leftHandSide '[' expression ']'                    # IndexExpr
  | leftHandSide '.' Identifier                        # PropertyAccessExpr
  ;

primaryAtom
  : Identifier                                         # IdentifierExpr
  | 'new' Identifier '(' ')'                           # NewExprNoArgs
  | 'new' Identifier '(' argumentList ')'              # NewExprWithArgs
  | 'this'                                             # ThisExpr
  ;

argumentList
  : argumentList ',' expression                        # MoreArguments
  | expression                                         # FirstArgument
  ;

arrayLiteral
  : '[' ']'                                            # EmptyArrayLiteral
  | '[' elementList ']'                                # NonEmptyArrayLiteral
  ;

elementList
  : elementList ',' expression                         # MoreElements
  | expression                                         # FirstElement
  ;

// ------------------
// Types
// ------------------

type: baseType ('[' ']')*;
baseType: 'boolean' | 'integer' | 'string' | Identifier;

// ------------------
// Lexer Rules
// ------------------

IntegerLiteral: [0-9]+;
StringLiteral: '"' (~["\r\n])* '"';

Identifier: [a-zA-Z_][a-zA-Z0-9_]*;

WS: [ \t\r\n]+ -> skip;
COMMENT: '//' ~[\r\n]* -> skip;
MULTILINE_COMMENT: '/*' .*? '*/' -> skip;
