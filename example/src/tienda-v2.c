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
    if (subtotal >= 75.0) {
        return 0.0;
    }
    return 5.0;
}

double calcular_descuento(double subtotal, int cliente_vip)
{
    if (cliente_vip) {
        return subtotal * 0.10;
    }
    return 0.0;
}

void mostrar_pedido(const double precios[], size_t cantidad, int cliente_vip)
{
    if (precios == NULL || cantidad == 0) {
        puts("Pedido vacio");
        return;
    }

    for (size_t i = 0; i < cantidad; ++i) {
        if (precios[i] < 0.0) {
            printf("Precio invalido en el producto %zu\n", i + 1);
            return;
        }
    }

    double subtotal = calcular_subtotal(precios, cantidad);
    double descuento = calcular_descuento(subtotal, cliente_vip);
    double envio = calcular_envio(subtotal);
    double total = subtotal - descuento + envio;

    puts("Resumen del pedido");
    printf("Productos: %zu\n", cantidad);
    printf("Subtotal: %.2f EUR\n", subtotal);
    printf("Descuento: %.2f EUR\n", descuento);
    printf("Envio: %.2f EUR\n", envio);
    printf("Total: %.2f EUR\n", total);
}

int main(void)
{
    const double precios[] = {20.0, 15.0, 25.0};
    size_t cantidad = sizeof precios / sizeof precios[0];
    mostrar_pedido(precios, cantidad, 1);
    return 0;
}
