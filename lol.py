import itertools

def value(v, i, xx):
    return sum(v[i][j] for j in xx)

def inverse(n, m, x_inv):
    x = [[] for _ in range(n)]
    for i in range(m):
        x[x_inv[i]].append(i)
    return x

def gen_inv_allocations(n, m):
    x_inv = itertools.product(range(n), repeat=m)
    for alloc in x_inv:
        yield alloc
        
def gen_valuation(n, m, v_max):
    v = itertools.product(range(0, v_max + 1), repeat=n * m)
    for valuation in v:
        yield [list(valuation[i * m:(i + 1) * m]) for i in range(n)]
        

def perato_optimal(n, m, v, x):
    for x_bar_inv in gen_inv_allocations(n, m):
        x_bar = inverse(n, m, x_bar_inv)
        first_expression = False
        for i in range(n):
            if value(v, i, x[i]) > value(v, i, x_bar[i]):
                first_expression = True
                break
        second_expression = True
        for i in range(n):
            if value(v, i, x[i]) >= value(v, i, x_bar[i]):
                second_expression = False
                break
        if first_expression or second_expression:
            return True
    return False

def efx(n, m, v, x):
    for i in range(n):
        for j in range(n):
            for k in x[j]:
                if value(v, i, x[i]) < value(v, i, [item for item in x[j] if item != k]):
                    return False
    return True

def check_efx_and_perato_optimal(n, m, v):
    for x_inv in gen_inv_allocations(n, m):
        x = inverse(n, m, x_inv)
        if efx(n, m, v, x) and perato_optimal(n, m, v, x):
            return
    print("No EFX and Pareto optimal allocation found for n =", n, "m =", m, "v =", v)
    
def main():
    n = 2  # number of agents
    m = 3  # number of items
    v_max = 10  # maximum valuation

    for v in gen_valuation(n, m, v_max):
        check_efx_and_perato_optimal(n, m, v)
        
if __name__ == "__main__":
    main()