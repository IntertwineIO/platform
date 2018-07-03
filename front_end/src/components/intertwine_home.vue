<template>
  <main class="intertwine__home stage">
    <h1>{{ headline }}</h1>
    <geoSearch></geoSearch>
    <p>{{ blurb }}</p>
  </main>
</template>

<script>
export default {
  name: 'IntertwineHome',
  components: {
    geoSearch: () => import('@/components/geo_search')
  },
  data () {
    return {
      headline: 'Untangle the world’s problems',
      blurb: 'Collaborate with doers, dreamers, and data geeks to tackle pressing social issues'
    }
  }
}
</script>

<style lang="scss" scoped>
@import '~@/sass/palette.scss';
@import '~@/sass/_mixins.scss';

.intertwine__home {
  width: 70vw;
  margin: 0 auto;
  text-align: center;
  height: 100%;

  nav {
    margin-top: 1rem;
    border-top: 1px solid rgba(0,0,0,.05);
    display: flex;
    justify-content: space-evenly;
    align-items: stretch;
    align-content: stretch;

    a {
      display: block;
      width: 39%;
      padding: 1rem 3rem;
      text-transform: uppercase;
      transition: all .2s;
      font-size: 1.25rem;
      color: red;

      &:hover {
        @include accent_texture;
        color: $gold;
      }
    }
  }

  h1 {
    color: $red;
    margin-bottom: 0;
  }
}
</style>
