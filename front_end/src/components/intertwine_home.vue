<template>
  <main class="intertwine__home stage">
    <h1>{{ headline }}</h1>
    <p>{{ blurb }}</p>

    <EmailCapture></EmailCapture>

    <nav>
      <router-link :to="{ name: 'communities'}">By Community</router-link>
      <router-link :to="{ name: 'problems'}">By Problem</router-link>
    </nav>
  </main>
</template>

<script>
export default {
  name: 'IntertwineHome',
  components: {
    EmailCapture: () => import('@/components/home/email_capture')
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

.intertwine__home {
  width: 70vw;
  margin: 0 auto;
  text-align: center;

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
      padding: 2rem 3rem;
      text-transform: uppercase;
      transition: all .2s;
      font-size: 1.25rem;
      color: red;

      &:hover {
        background: $red;
        color: $gold;
      }
    }
  }

  h1 {
    color: $red;
    margin-bottom: 0;
  }
}

.vue2leaflet-map {
  height: 50vh !important;
}
</style>
