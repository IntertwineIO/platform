<template>
  <main class="intertwine__communities stage">
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

<style>
.vue2leaflet-map {
  height: 70vh;
}
</style>
