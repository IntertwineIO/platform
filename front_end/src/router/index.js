import Vue from 'vue'
import Router from 'vue-router'
import IntertwineHome from '@/components/intertwine_home'
import IntertwineCommunities from '@/components/intertwine_communities'

Vue.use(Router)

export default new Router({
  routes: [
    {
      path: '/',
      name: 'IntertwineHome',
      component: IntertwineHome
    },
    {
      path: '/communities',
      name: 'IntertwineCommunities',
      component: IntertwineCommunities
    }
  ]
})

// const routerOptions = [
//   { path: '/', component: IntertwineHome },
//   { path: '/about', component: IntertwineCommunities }
// ]
// const routes = routerOptions.map(route => {
//   return {
//     ...route,
//     component: () => import(`@/components/${route.component}.vue`)
//   }
// })
// Vue.use(Router)
// export default new Router({
//   routes,
//   mode: 'history'
// })
