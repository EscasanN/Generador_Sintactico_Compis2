global:
    static[0]@i = 0
    while_cond0:
    t0 = static[0]@i
    t1 = t0 < 10
    release t0
    ifFalse t1 goto while_end1
    t0 = static[0]@i
    t2 = t0 + 1
    release t0
    static[0]@i = t2
    release t2
    t2 = static[0]@i
    t3 = t2 == 2
    release t2
    ifFalse t3 goto if_end2
    goto while_cond0
    if_end2:
    release t3
    t2 = static[0]@i
    t3 = t2 == 8
    release t2
    ifFalse t3 goto if_end3
    goto while_end1
    if_end3:
    release t3
    goto while_cond0
    while_end1:
    release t1
    static[4]@j = 0
    do_body4:
    t2 = static[4]@j
    t0 = t2 + 1
    release t2
    static[4]@j = t0
    release t0
    t0 = static[4]@j
    t1 = t0 == 1
    release t0
    ifFalse t1 goto if_end7
    goto do_cond5
    if_end7:
    release t1
    do_cond5:
    t0 = static[4]@j
    t1 = t0 < 3
    release t0
    if t1 goto do_body4
    release t1
    do_end6:
    static[8]@k = 0
    for_cond8:
    t0 = static[8]@k
    t1 = t0 < 3
    release t0
    ifFalse t1 goto for_end10
    static[16]@m = 0
    for_cond11:
    t0 = static[16]@m
    t3 = t0 < 3
    release t0
    ifFalse t3 goto for_end13
    t0 = static[16]@m
    t4 = t0 == 1
    release t0
    ifFalse t4 goto if_end14
    goto for_end13
    if_end14:
    release t4
    t0 = static[8]@k
    t4 = t0 == 1
    release t0
    ifFalse t4 goto if_end15
    goto for_update12
    if_end15:
    release t4
    for_update12:
    t0 = static[16]@m
    t2 = t0 + 1
    release t0
    static[16]@m = t2
    release t2
    goto for_cond11
    for_end13:
    release t3
    for_update9:
    t2 = static[8]@k
    t0 = t2 + 1
    release t2
    static[8]@k = t0
    release t0
    goto for_cond8
    for_end10:
    release t1
    static[12]@p = 0
    for_cond16:
    t0 = static[12]@p
    t1 = t0 < 2
    release t0
    ifFalse t1 goto for_end18
    t0 = static[12]@p
    t2 = t0 + 1
    release t0
    static[12]@p = t2
    release t2
    for_update17:
    goto for_cond16
    for_end18:
    release t1
    static[12]@p = 0
    for_cond19:
    t2 = static[12]@p
    t1 = t2 > 2
    release t2
    ifFalse t1 goto if_end22
    goto for_end21
    if_end22:
    release t1
    for_update20:
    t2 = static[12]@p
    t0 = t2 + 1
    release t2
    static[12]@p = t0
    release t0
    goto for_cond19
    for_end21:
    for_cond23:
    goto for_end25
    for_end25:
