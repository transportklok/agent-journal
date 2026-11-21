import {createApp, h, nextTick} from "vue";
import {afterEach, expect, test, vi} from "vitest";
import {store} from "../src/state/store.js";

const at = (seconds) => new Date(seconds * 1000).toISOString();
const row = (id, state) => ({id, name: "Mary", brief: `job ${id}`, model: "sonnet", state, created_at: at(1000), updated_at: at(1100)});
const rows = vi.hoisted(() => ({value: []}));

vi.mock("../src/composables/workers.js", async () => {
    const {computed} = await import("vue");
    return {useWorkers: () => ({rows: computed(() => rows.value)}), useWorkersShown: () => ({rows: computed(() => [])})};
});
vi.mock("../src/composables/leadAgent.js", () => ({agent: {value: null}}));

const {default: AgentGrid} = await import("../src/agents/AgentGrid.vue");

let app = null;
afterEach(() => {
    app?.unmount();
    app = null;
    document.body.innerHTML = "";
});

test("the grid draws running and troubled workers first and folds the closed ones into a group that opens", async () => {
    store.summary = {environments: []};
    rows.value = [row(1, "merged"), row(2, "dispatched"), row(3, "released"), row(4, "ended without clocking out"), row(5, "stopped")];
    const host = document.body.appendChild(document.createElement("div"));
    app = createApp({render: () => h(AgentGrid)});
    app.mount(host);
    await nextTick();
    const names = () => [...host.querySelectorAll(".agent-window .aw-state")].map((el) => el.textContent);
    expect(names()).toEqual(["Working", "Ended without clocking out", "Stopped"]);
    const fold = host.querySelector("[data-closed-fold]");
    expect(fold.textContent.trim()).toBe("Show 2 closed agents");
    expect(fold.getAttribute("aria-expanded")).toBe("false");
    fold.click();
    await nextTick();
    expect(names()).toEqual(["Working", "Ended without clocking out", "Stopped", "Merged", "Released"]);
    expect(host.querySelector("[data-closed-fold]").textContent.trim()).toBe("Hide 2 closed agents");
});

test("a grid with no closed worker has no fold", async () => {
    store.summary = {environments: []};
    rows.value = [row(2, "dispatched")];
    const host = document.body.appendChild(document.createElement("div"));
    app = createApp({render: () => h(AgentGrid)});
    app.mount(host);
    await nextTick();
    expect(host.querySelector("[data-closed-fold]")).toBe(null);
});
