BASE DE DATOS 

| Tabla                     | Para qué sirve                                       |
| ------------------------- | ---------------------------------------------------- |
| **`destinations`**        | Guarda la URL real de destino                        |
| **`slugs`**               | El nombre corto editable (`code`) + token de edición |
| **`slug_history`**        | Auditoría: quién renombró qué y cuándo               |
| **`destination_history`** | Auditoría: cambios de URL destino                    |
| **`clicks`**              | Cada redirección = 1 fila (analytics)                |
