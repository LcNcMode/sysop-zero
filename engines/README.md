# engines/ — shared code

Reusable building blocks for prods: tiny synths, tracker players, effect libraries, packers,
intro frameworks. Everything here is **MIT** (see `LICENSE`), so any prod can use it, whatever
the prod's own license.

## Add an engine

One folder per engine, `engines/<name>/`, with a `README.md` that says:

- what it does, and a minimal example;
- its size cost (bytes added to an intro), if it is meant for intros;
- its license, if it is not MIT (third-party code keeps its own license text).

## Use an engine

Copy the engine files into your prod folder and credit the engine in your `nfo.txt`.
The gallery only publishes prod folders, so a web prod must ship everything it loads.
Greetings to the engine's author are always good form.

No engines yet. The first one sets the standard.
