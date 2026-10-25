#include <stddef.h>
#include <stdio.h>

double calcular_subtotal(const double precios[], size_t cantidad)
{
    double subtotal = 0.0;
    for (size_t i = 0; i < cantidad; ++i) {
        subtotal += precios[i];
    }
    return subtotal;
}

double calcular_envio(double subtotal)
{
    if (subtotal >= 50.0) {
        return 0.0;
    }
    return 5.0;
}

void mostrar_pedido(const double precios[], size_t cantidad, int cliente_vip)
{
    (void)cliente_vip;
    double subtotal = calcular_subtotal(precios, cantidad);
    double envio = calcular_envio(subtotal);
    printf("Total: %.2f EUR\n", subtotal + envio);
}

void mensaje_bienvenida(void)
{
    puts("Bienvenido a la tienda");
}


int main(void)
{
    mensaje_bienvenida();
    const double precios[] = {20.0, 15.0, 25.0};
    size_t cantidad = sizeof precios / sizeof precios[0];
    mostrar_pedido(precios, cantidad, 1);
    return 0;
}
