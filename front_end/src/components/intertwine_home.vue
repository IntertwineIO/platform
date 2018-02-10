<template>
  <main id="intertwine__home">
    <h1>{{ headline }}</h1>
    <p>{{ blurb }}</p>
  </main>
</template>

<script>
export default {
  name: 'IntertwineHome',
  data () {
    return {
      headline: 'Untangle the world’s problems',
      blurb: 'Collaborate with doers, dreamers, and data geeks to tackle pressing social issues'
    }
  }
}
</script>
