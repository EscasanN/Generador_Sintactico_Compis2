global:
    static[0]@a = 6
    static[4]@b = 4
    t0 = static[0]@a
    t1 = t0 + static[4]@b
    release t0
    t0 = static[0]@a
    t2 = t0 - static[4]@b
    release t0
    t0 = t1 * t2
    release t1
    release t2
    t2 = t0 / 2
    release t0
    t0 = t2 % 7
    release t2
    static[8]@expresion = t0
    release t0
    t0 = static[0]@a
    t3 = t0 > 0
    release t0
    t4 = t3
    release t3
    ifFalse t4 goto logic_end0
    t0 = static[4]@b
    t3 = t0 < 10
    release t0
    t4 = t3
    release t3
    logic_end0:
    t3 = t4
    release t4
    if t3 goto logic_end1
    t0 = static[0]@a
    t4 = t0 == static[4]@b
    release t0
    t5 = !t4
    release t4
    t3 = t5
    release t5
    logic_end1:
    static[12]@enRango = t3
    release t3
    t0 = static[0]@a
    t3 = t0 > static[4]@b
    release t0
    ifFalse t3 goto ternary_false2
    t0 = static[0]@a
    goto ternary_end3
    ternary_false2:
    t0 = static[4]@b
    ternary_end3:
    release t3
    static[16]@mayor = t0
    release t0
    param 5
    t0 = call fn_factorial, 1
    static[20]@fact = t0
    release t0
    param 1
    t0 = call fn_acumulador, 1
    static[24]@acumulado = t0
    release t0
    t6 = object_new CuentaAhorro, 24
    param t6
    call CuentaAhorro.constructor, 1
    static[32]@cuenta = t6
    release t6
    param static[32]@cuenta
    param 100
    call Cuenta.depositar, 2
    param static[32]@cuenta
    t7 = call CuentaAhorro.interes, 1
    static[40]@interes = t7
    release t7
    t8 = object_new Cuenta, 16
    param t8
    param "Ana"
    param 50
    call Cuenta.constructor, 3
    static[48]@corriente = t8
    release t8
    param static[48]@corriente
    param 25
    t0 = call Cuenta.depositar, 2
    static[56]@saldo = t0
    release t0
    t9 = list_new 5
    list_set t9, 0, 3
    list_set t9, 1, 1
    list_set t9, 2, 4
    list_set t9, 3, 1
    list_set t9, 4, 5
    static[64]@numeros = t9
    release t9
    t0 = list_get static[64]@numeros, 1
    t2 = list_get static[64]@numeros, 2
    t1 = t0 + t2
    release t0
    release t2
    list_set static[64]@numeros, 0, t1
    release t1
    static[72]@suma = 0
    t9 = static[64]@numeros
    t1 = list_len t9
    t2 = 0
    foreach_cond4:
    t3 = t2 < t1
    ifFalse t3 goto foreach_end6
    static[84]@n = list_get t9, t2
    t0 = static[84]@n
    t5 = t0 == 1
    release t0
    ifFalse t5 goto if_end7
    goto foreach_next5
    if_end7:
    release t5
    t0 = static[72]@suma
    t10 = t0 + static[84]@n
    release t0
    static[72]@suma = t10
    release t10
    foreach_next5:
    t2 = t2 + 1
    goto foreach_cond4
    foreach_end6:
    release t3
    release t2
    release t1
    release t9
    static[76]@i = 0
    while_cond8:
    t1 = static[76]@i
    t3 = t1 < 3
    release t1
    ifFalse t3 goto while_end9
    t1 = static[76]@i
    t2 = t1 + 1
    release t1
    static[76]@i = t2
    release t2
    goto while_cond8
    while_end9:
    release t3
    do_body10:
    t2 = static[76]@i
    t1 = t2 - 1
    release t2
    static[76]@i = t1
    release t1
    do_cond11:
    t1 = static[76]@i
    t3 = t1 > 0
    release t1
    if t3 goto do_body10
    release t3
    do_end12:
    static[80]@k = 0
    for_cond13:
    t1 = static[80]@k
    t3 = t1 < 5
    release t1
    ifFalse t3 goto for_end15
    t1 = static[80]@k
    t5 = t1 == 3
    release t1
    ifFalse t5 goto if_end16
    goto for_end15
    if_end16:
    release t5
    param static[80]@k
    call print, 1
    for_update14:
    t1 = static[80]@k
    t2 = t1 + 1
    release t1
    static[80]@k = t2
    release t2
    goto for_cond13
    for_end15:
    release t3
    t2 = static[72]@suma
    t1 = t2 % 3
    release t2
    t3 = t1 == 0
    release t1
    t5 = t3 == true
    if t5 goto switch_case17
    t1 = static[72]@suma
    t4 = t1 > 10
    release t1
    t5 = t3 == t4
    release t4
    if t5 goto switch_case18
    goto switch_default19
    switch_case17:
    param "multiplo de tres"
    call print, 1
    switch_case18:
    param "mayor que diez"
    call print, 1
    switch_default19:
    param "otro resto"
    call print, 1
    switch_end20:
    release t5
    release t3

procedure Cuenta.constructor(parameter:Cuenta.constructor[32]@this, parameter:Cuenta.constructor[40]@titular, parameter:Cuenta.constructor[48]@saldo):
    field_set parameter:Cuenta.constructor[32]@this, 0, parameter:Cuenta.constructor[40]@titular
    field_set parameter:Cuenta.constructor[32]@this, 8, parameter:Cuenta.constructor[48]@saldo
    return

procedure Cuenta.depositar(parameter:Cuenta.depositar[32]@this, parameter:Cuenta.depositar[40]@monto):
    t0 = field_get parameter:Cuenta.depositar[32]@this, 8
    t1 = t0 + parameter:Cuenta.depositar[40]@monto
    release t0
    field_set parameter:Cuenta.depositar[32]@this, 8, t1
    release t1
    t1 = field_get parameter:Cuenta.depositar[32]@this, 8
    return t1

procedure CuentaAhorro.constructor(parameter:CuentaAhorro.constructor[32]@this):
    field_set parameter:CuentaAhorro.constructor[32]@this, 16, 0.05
    return

procedure CuentaAhorro.interes(parameter:CuentaAhorro.interes[32]@this):
    t0 = field_get parameter:CuentaAhorro.interes[32]@this, 8
    t1 = cast float t0
    release t0
    t2 = field_get parameter:CuentaAhorro.interes[32]@this, 16
    t3 = t1 * t2
    release t1
    release t2
    return t3

procedure fn_factorial(parameter:fn_factorial[32]@n):
    t0 = parameter:fn_factorial[32]@n
    t1 = t0 <= 1
    release t0
    ifFalse t1 goto if_end21
    return 1
    if_end21:
    release t1
    t0 = parameter:fn_factorial[32]@n
    t2 = parameter:fn_factorial[32]@n
    t3 = t2 - 1
    release t2
    param t3
    t2 = call fn_factorial, 1
    release t3
    t3 = t0 * t2
    release t0
    release t2
    return t3

procedure fn_acumulador(parameter:fn_acumulador[32]@inicio):
    t0 = env_new 16
    env_set t0, 0, parameter:fn_acumulador[32]@inicio
    t1 = closure fn_acumulador.sumar, t0
    param 5
    closure_call t1, 1
    release t1
    t1 = closure fn_acumulador.sumar, t0
    param 10
    t2 = closure_call t1, 1
    release t1
    return t2

procedure fn_acumulador.sumar(parameter:fn_acumulador.sumar[32]@env, parameter:fn_acumulador.sumar[40]@valor):
    t0 = env_get parameter:fn_acumulador.sumar[32]@env, 0:0
    t1 = t0 + parameter:fn_acumulador.sumar[40]@valor
    release t0
    env_set parameter:fn_acumulador.sumar[32]@env, 0:0, t1
    release t1
    t1 = env_get parameter:fn_acumulador.sumar[32]@env, 0:0
    return t1
