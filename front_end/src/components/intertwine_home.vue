<template>
  <main id="intertwine__home">
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
#intertwine__home {
  width: 50vw;
  background: rgba(0,0,0,.25);
  margin: 0 auto;
  padding: 2rem;
}
</style>
