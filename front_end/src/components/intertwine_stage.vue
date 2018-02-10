<template>
  <main id="intertwine__stage">
    <h1>{{ headline }}</h1>
    <p>{{ blub }}</p>
  </main>
</template>

<script>
export default {
  name: 'IntertwineStage',
  data () {
    return {
      headline: 'Untangle the world’s problems',
      blurb: 'Collaborate with doers, dreamers, and data geeks to tackle pressing social issues'
    }
  }
}
</script>

<style scoped>
  h1, h2 {
    font-weight: normal;
  }
  ul {
    list-style-type: none;
    padding: 0;
  }
  li {
    display: inline-block;
    margin: 0 10px;
  }
  a {
    color: #42b983;
  }
</style>
