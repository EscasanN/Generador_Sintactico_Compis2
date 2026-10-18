global:
    t0 = list_new 0
    static[0]@vacia = t0
    release t0
    t1 = list_new 3
    list_set t1, 0, 5
    list_set t1, 1, 6
    list_set t1, 2, 7
    static[8]@numeros = t1
    release t1
    t2 = list_new 2
    t1 = list_new 2
    list_set t1, 0, 1
    list_set t1, 1, 2
    list_set t2, 0, t1
    release t1
    t1 = list_new 2
    list_set t1, 0, 3
    list_set t1, 1, 4
    list_set t2, 1, t1
    release t1
    static[16]@matriz = t2
    release t2
    t3 = list_get static[8]@numeros, 0
    static[24]@primero = t3
    release t3
    t3 = list_get static[8]@numeros, 0
    t4 = list_get static[8]@numeros, 1
    t5 = t3 + t4
    release t3
    release t4
    list_set static[8]@numeros, 2, t5
    release t5
    t1 = list_get static[16]@matriz, 1
    t5 = list_get t1, 0
    release t1
    static[28]@esquina = t5
    release t5
    t1 = list_get static[16]@matriz, 0
    list_set t1, 1, static[28]@esquina
    release t1
    static[32]@total = 0
    t1 = static[8]@numeros
    t5 = list_len t1
    t4 = 0
    foreach_cond0:
    t6 = t4 < t5
    ifFalse t6 goto foreach_end2
    static[36]@n = list_get t1, t4
    t3 = static[32]@total
    t7 = t3 + static[36]@n
    release t3
    static[32]@total = t7
    release t7
    foreach_next1:
    t4 = t4 + 1
    goto foreach_cond0
    foreach_end2:
    release t6
    release t4
    release t5
    release t1
