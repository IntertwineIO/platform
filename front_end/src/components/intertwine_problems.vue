<template>
  <main id="intertwine__problems">
    <h1>{{ headline }}</h1>
    <p>{{ blurb }}</p>
  </main>
</template>

<script>
export default {
  name: 'IntertwineProblems',
  data () {
    return {
      headline: 'Find a problem',
      blurb: 'Some blurb here about Problems'
    }
  }
}
</script>
