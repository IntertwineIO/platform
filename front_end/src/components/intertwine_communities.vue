<template>
  <main id="intertwine__communities">
    <h1>{{ headline }}</h1>
    <p>{{ blurb }}</p>
  </main>
</template>

<script>
export default {
  name: 'IntertwineCommunities',
  data () {
    return {
      headline: 'Find a problem by commmunity',
      blurb: 'Some blurb here about Communities'
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
