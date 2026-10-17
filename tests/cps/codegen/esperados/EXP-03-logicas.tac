global:
    static[0]@a = 4
    static[4]@b = 9
    t0 = static[0]@a
    t1 = t0 == static[4]@b
    release t0
    static[8]@igual = t1
    release t1
    t0 = static[0]@a
    t1 = t0 != static[4]@b
    release t0
    static[9]@distinto = t1
    release t1
    t0 = static[0]@a
    t1 = t0 < static[4]@b
    release t0
    static[10]@menor = t1
    release t1
    t0 = static[0]@a
    t1 = t0 <= static[4]@b
    release t0
    static[11]@menorIgual = t1
    release t1
    t0 = static[0]@a
    t1 = t0 > static[4]@b
    release t0
    static[12]@mayor = t1
    release t1
    t0 = static[0]@a
    t1 = t0 >= static[4]@b
    release t0
    static[13]@mayorIgual = t1
    release t1
    t0 = static[0]@a
    t1 = t0 < static[4]@b
    release t0
    t2 = t1
    release t1
    ifFalse t2 goto logic_end0
    t0 = static[4]@b
    t1 = t0 > 0
    release t0
    t2 = t1
    release t1
    logic_end0:
    static[14]@ambos = t2
    release t2
    t0 = static[0]@a
    t2 = t0 > static[4]@b
    release t0
    t1 = t2
    release t2
    if t1 goto logic_end1
    t0 = static[4]@b
    t2 = t0 != 0
    release t0
    t1 = t2
    release t2
    logic_end1:
    static[15]@alguno = t1
    release t1
    t0 = static[0]@a
    t1 = t0 < static[4]@b
    release t0
    t2 = t1
    release t1
    if t2 goto logic_end2
    t0 = static[0]@a
    t1 = t0 == 0
    release t0
    t2 = t1
    release t1
    logic_end2:
    t1 = t2
    release t2
    ifFalse t1 goto logic_end3
    t0 = static[4]@b
    t2 = t0 == 0
    release t0
    t3 = !t2
    release t2
    t1 = t3
    release t3
    logic_end3:
    static[16]@combinado = t1
    release t1
    t0 = static[0]@a
    t1 = t0 > static[4]@b
    release t0
    ifFalse t1 goto ternary_false4
    t0 = static[0]@a
    goto ternary_end5
    ternary_false4:
    t0 = static[4]@b
    ternary_end5:
    release t1
    static[20]@maximo = t0
    release t0
