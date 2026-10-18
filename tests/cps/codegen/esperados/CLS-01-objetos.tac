global:
    t0 = object_new Punto, 8
    param t0
    param 1
    param 2
    call Punto.constructor, 3
    static[0]@p = t0
    release t0
    param static[0]@p
    param 3
    param 4
    call Punto.mover, 3
    param static[0]@p
    t1 = call Punto.distanciaManhattan, 1
    static[8]@d = t1
    release t1
    t2 = object_new Vacia, 8
    param t2
    call Vacia.constructor, 1
    static[16]@v = t2
    release t2
    t3 = field_get static[16]@v, 0
    static[24]@ok = t3
    release t3

procedure Punto.constructor(parameter:Punto.constructor[32]@this, parameter:Punto.constructor[40]@x, parameter:Punto.constructor[44]@y):
    field_set parameter:Punto.constructor[32]@this, 0, parameter:Punto.constructor[40]@x
    field_set parameter:Punto.constructor[32]@this, 4, parameter:Punto.constructor[44]@y
    return

procedure Punto.mover(parameter:Punto.mover[32]@this, parameter:Punto.mover[40]@dx, parameter:Punto.mover[44]@dy):
    t0 = field_get parameter:Punto.mover[32]@this, 0
    t1 = t0 + parameter:Punto.mover[40]@dx
    release t0
    field_set parameter:Punto.mover[32]@this, 0, t1
    release t1
    t1 = field_get parameter:Punto.mover[32]@this, 4
    t0 = t1 + parameter:Punto.mover[44]@dy
    release t1
    field_set parameter:Punto.mover[32]@this, 4, t0
    release t0
    return

procedure Punto.distanciaManhattan(parameter:Punto.distanciaManhattan[32]@this):
    t0 = field_get parameter:Punto.distanciaManhattan[32]@this, 0
    t1 = field_get parameter:Punto.distanciaManhattan[32]@this, 4
    t2 = t0 + t1
    release t0
    release t1
    return t2

procedure Vacia.constructor(parameter:Vacia.constructor[32]@this):
    field_set parameter:Vacia.constructor[32]@this, 0, true
    return
