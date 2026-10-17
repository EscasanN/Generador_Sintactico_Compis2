global:
    param 10
    t0 = call fn_contador, 1
    static[0]@resultado = t0
    release t0

procedure fn_contador(parameter:fn_contador[32]@inicio):
    t0 = env_new 16
    env_set t0, 0, parameter:fn_contador[32]@inicio
    t1 = closure fn_contador.incrementar, t0
    param 1
    closure_call t1, 1
    release t1
    t1 = closure fn_contador.incrementar, t0
    param 2
    t2 = closure_call t1, 1
    release t1
    return t2

procedure fn_contador.incrementar(parameter:fn_contador.incrementar[32]@env, parameter:fn_contador.incrementar[40]@paso):
    t0 = env_new 8
    env_set t0, 0, parameter:fn_contador.incrementar[32]@env
    t1 = env_get parameter:fn_contador.incrementar[32]@env, 0:0
    t2 = t1 + parameter:fn_contador.incrementar[40]@paso
    release t1
    env_set parameter:fn_contador.incrementar[32]@env, 0:0, t2
    release t2
    t3 = closure fn_contador.incrementar.doble, t0
    t2 = closure_call t3, 0
    release t3
    return t2

procedure fn_contador.incrementar.doble(parameter:fn_contador.incrementar.doble[32]@env):
    t0 = env_get parameter:fn_contador.incrementar.doble[32]@env, 1:0
    t1 = t0 * 2
    release t0
    return t1
