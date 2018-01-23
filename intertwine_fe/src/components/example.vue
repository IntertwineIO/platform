<template>
  <main
    class="hello"
    v-on:mousemove="handleMouseMove"
  >
    <h1>{{ msg }}</h1>

    <section class="hello__mouse_instructions" v-show="!mouse.x && !mouse.y">
      Move your mouse to prove it
    </section>

    <section class="hello__mouse_display" v-show="mouse.x || mouse.y">
      Your mouse is at <strong>X: {{ mouse.x }}, Y: {{ mouse.y }}</strong>
    </section>

  </main>
</template>

<script>
export default {
  data() {
    return {
      msg: 'Vue is up and running within Intertwine',
      mouse: {
        x: null,
        y: null,
      },
    };
  },
  methods: {
    handleMouseMove(event) {
      this.mouse.x = event.pageX;
      this.mouse.y = event.pageY;
    },
  },
};
</script>

<style lang="scss">
$pale: #EFF3CD;
$bg_light: #B2D5BA;
$bg: #61ADA0;
$bg_dark: #248F8D;
$purple: #605063;

  body {
    min-height: 100%;
    font-family: 'Avenir', Helvetica, Arial, sans-serif;
    -webkit-font-smoothing: antialiased;
    -moz-osx-font-smoothing: grayscale;
    text-align: center;
    margin: 0;
    padding-top: 2rem;
    background-color: #eff3cd;
    background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='16' height='32' viewBox='0 0 16 32'%3E%3Cg fill='%2361ada0' fill-opacity='0.4'%3E%3Cpath fill-rule='evenodd' d='M0 24h4v2H0v-2zm0 4h6v2H0v-2zm0-8h2v2H0v-2zM0 0h4v2H0V0zm0 4h2v2H0V4zm16 20h-6v2h6v-2zm0 4H8v2h8v-2zm0-8h-4v2h4v-2zm0-20h-6v2h6V0zm0 4h-4v2h4V4zm-2 12h2v2h-2v-2zm0-8h2v2h-2V8zM2 8h10v2H2V8zm0 8h10v2H2v-2zm-2-4h14v2H0v-2zm4-8h6v2H4V4zm0 16h6v2H4v-2zM6 0h2v2H6V0zm0 24h2v2H6v-2z'/%3E%3C/g%3E%3C/svg%3E");
    border-top: 10px solid $purple;
  }
  .hello {
    min-height: 40rem;
    color: $purple;
  }
</style>
