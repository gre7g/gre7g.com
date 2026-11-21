// Vite entry point: create the application singleton and start it up.
import { Main } from "./main";

export let G_MAIN = new Main();

G_MAIN.main();
