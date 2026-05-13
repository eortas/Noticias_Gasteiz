# Automatización en Windows (Cron Job)

Este repositorio incluye un script silencioso diseñado para ser ejecutado automáticamente por el **Programador de Tareas de Windows**.

## 🚀 Cómo crear la tarea (Cada 15 minutos)

Para programar la actualización automática cada 15 minutos, abre una terminal (PowerShell o CMD) como **Administrador** y ejecuta el siguiente comando:

```batch
schtasks /create /sc minute /mo 15 /tn "ActualizadorNoticiasGasteiz" /tr "C:\Users\ortas\OneDrive\Documentos\Noticias_Gasteiz\update_news_silent.bat" /it
```

> [!IMPORTANT]
> Asegúrate de que la ruta coincida con la ubicación real de tu proyecto.

## 🗑️ Cómo borrar la tarea

Si deseas detener la automatización y eliminar la tarea programada, ejecuta este comando como **Administrador**:

```batch
schtasks /delete /tn "ActualizadorNoticiasGasteiz" /f
```

## 📝 Notas adicionales
- La tarea solo se ejecutará cuando el ordenador esté encendido y hayas iniciado sesión.
- Se utiliza el archivo `update_news_silent.bat` porque no tiene pausas (`pause`), lo que permite que el proceso termine solo sin intervención humana.
- Puedes verificar el estado de la tarea buscando "Programador de Tareas" en el menú de inicio de Windows.
