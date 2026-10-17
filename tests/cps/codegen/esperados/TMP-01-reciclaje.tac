global:
    static[0]@a = 1
    static[4]@b = 2
    static[8]@c = 3
    static[12]@d = 4
    t0 = static[0]@a
    t1 = t0 + static[4]@b
    release t0
    t0 = static[8]@c
    t2 = t0 + static[12]@d
    release t0
    t0 = t1 * t2
    release t1
    release t2
    static[16]@r1 = t0
    release t0
    t0 = static[0]@a
    t2 = t0 * static[4]@b
    release t0
    t0 = static[8]@c
    t1 = t0 * static[12]@d
    release t0
    t0 = t2 + t1
    release t2
    release t1
    t1 = static[0]@a
    t2 = t1 - static[12]@d
    release t1
    t1 = t0 - t2
    release t0
    release t2
    static[20]@r2 = t1
    release t1
    t1 = static[0]@a
    t2 = t1 + static[4]@b
    release t1
    t1 = static[8]@c
    t0 = t1 + static[12]@d
    release t1
    t1 = t2 + t0
    release t2
    release t0
    t0 = static[0]@a
    t2 = t0 - static[4]@b
    release t0
    t0 = static[8]@c
    t3 = t0 - static[12]@d
    release t0
    t0 = t2 - t3
    release t2
    release t3
    t3 = t1 * t0
    release t1
    release t0
    static[24]@r3 = t3
    release t3
    t3 = static[0]@a
    t4 = t3 < static[4]@b
    release t3
    ifFalse t4 goto ternary_false0
    t3 = static[8]@c
    t6 = t3 > static[12]@d
    release t3
    t5 = t6
    release t6
    goto ternary_end1
    ternary_false0:
    t3 = static[0]@a
    t6 = t3 == static[12]@d
    release t3
    t5 = t6
    release t6
    ternary_end1:
    release t4
    static[28]@r4 = t5
    release t5
